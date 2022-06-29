from copy import deepcopy
from typing import List, Tuple
from base64 import b64encode
import yaspin
from ImageBuilder import ImageBuilder, ImageType
from RandomSampler import RandomSampler
import time
import json
import os
import sys
import argparse
import asyncio
import shutil

import utils

# Image generation class
class ImageGenerator(object):
    seed: str                           # Randomness seed
    prev_batches: List[dict]            # Pre-existing images
    prev_picks: List[Tuple[int]]        # Pre-existing picks
    this_batch: List[dict]              # New images
    new_picks: List[Tuple[int]]         # New picks
    layer_names: List[str]              # Layer names
    variation_names: List[List[str]]    # Variation names for each layer

    layers: List[dict]

    def __init__(self, layers: List[dict], seed: str, prev_batches: List[dict], dup_cnt_limit: int) -> None:
        utils.set_progress_for_ui("Setup unique trait generator", 0, 1)
        self.layers = layers
        self.seed = seed

        self.prev_batches = []
        self.prev_picks = []
        self.layer_names = [str(l["layer_name"]) for l in self.layers]   # Extract layer names
        self.variation_names = [ # Extract variation names from layers
            [str(rgba) for rgba in l["rgba"].keys()] if "rgba" in l else [str(filename) for filename in l["filenames"].keys()]
            for l in self.layers
        ]

        # Try converting images  in the {layer_name: variation_name} format to picks
        try:
            for image in prev_batches:
                self.prev_batches.append({name: image[name] for name in self.layer_names})
                self.prev_picks.append(tuple(
                    [
                        self.variation_names[i].index(image[name])
                        for i, name in enumerate(self.layer_names)
                    ]
                ))
        except (ValueError, IndexError) as e:
            print(f"Unable to parse previous batches, continuing as if there were none")
            self.prev_batches = []
            self.prev_picks = []
        utils.set_progress_for_ui("Setup unique trait generator", 1, 1)

        self.this_batch = []
        self.new_picks = []

    def generate_images(self, starting_id: int, image_cnt: int) -> List[dict]:
        utils.set_progress_for_ui("Generate unique traits", 0, image_cnt)
        self.prev_batches.extend(self.this_batch)
        self.prev_picks.extend(self.new_picks)
        self.this_batch = []
        self.new_picks = []

        # Setup random sampler
        weights = [ [ float(w)/ 100 for w in l["weights"] ] for l in self.layers]
        rs = RandomSampler(weights, seed=self.seed)
        rs.add_samples(self.prev_picks)
        rs.set_progress_callback(
            lambda done, total: utils.set_progress_for_ui("Generate unique traits", done+1, total)
        )

        # Generate unique picks
        self.new_picks = rs.sample(image_cnt, range(starting_id, starting_id + image_cnt))

        # Convert picks to images in the {layer_name: variation_name} format
        for i, pick in enumerate(self.new_picks):
            image = {
                self.layer_names[layer_index]:
                    self.variation_names[layer_index][variation_index]
                for layer_index, variation_index in enumerate(pick)
            }
            image["ID"] = starting_id + i # Add ID
            self.this_batch.append(image)

        return self.this_batch

    # Sort the list by ID
    def sortID(e: dict) -> int:
        return e["ID"]

# Returns true if all images are unique
def all_images_unique(all_images: List[dict]) -> bool:
    # Remove IDs to make comparison to new image easier
    images = deepcopy(all_images)
    for img in images:
        img.pop("ID", None)
    seen = list()
    return not any(i in seen or seen.append(i) for i in images)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--count", help="Total number of images to generate", type=int, required=True)
    parser.add_argument("-e", "--empty", help="Empty the generated directory", action="store_true")
    parser.add_argument("--name", help="Collection name (lowercase, ascii only)", type=str)
    parser.add_argument("--id", help="Specify starting ID for images", type=int, default=1)
    parser.add_argument("--seed", help="Specify the randomness seed", type=str, default=None)
    parser.add_argument("-t", "--threaded", help="Generate 4 images at once instead of just 1", action="store_true")
    parser.add_argument("--php", help=argparse.SUPPRESS, action="store_true")
    args = parser.parse_args()
    return args

def make_directories(paths: utils.Struct, traits: utils.Struct, empty: bool):
    if empty:
        if os.path.exists(paths.images):
            shutil.rmtree(paths.images)
        if os.path.exists(paths.thumbnails):
            shutil.rmtree(paths.thumbnails)
        if os.path.exists(paths.all_traits):
            os.remove(paths.all_traits)
        if os.path.exists(paths.gen_stats):
            os.remove(paths.gen_stats)

    # Make paths if they don't exist
    if not os.path.exists(paths.images):
        os.makedirs(paths.images)
    if not os.path.exists(paths.metadata):
        os.makedirs(paths.metadata)
    if not os.path.exists(paths.thumbnails) and traits.thumbnails:
        os.makedirs(paths.thumbnails)

# Image builder functions
async def build_and_save_image(paths: utils.Struct, traits: utils.Struct, item: dict, task_id: int):
    with ImageBuilder(animated_format=traits.animated_format) as img_builder:
        for l in traits.image_layers:
            layer_pretty_name = item[l["layer_name"]]

            if l["type"] == "filenames":
                layer_file = os.path.join(l["path"], l["filenames"][layer_pretty_name])
                img_builder.overlay_image(layer_file)
            elif l["type"] == "rgba":
                if not "size" in l:
                    sys.exit(f"Missing image size for {l['layer_name']}")
                img_builder.overlay_image(tuple(l["rgba"][layer_pretty_name]), size=l["size"])

        # Composite all layers on top of each others
        composite = await img_builder.build()
        if traits.thumbnails:
            thumbnail = await img_builder.thumbnail(size=traits.thumbnail_size)

        if composite.type == ImageType.STATIC:
            file_path = os.path.join(paths.images, f"{traits.collection_lower}_{item['ID']:03}.png")
            composite.img.save(file_path)
            os.chmod(file_path, 0o777)
            if traits.thumbnails:
                thumb_path = os.path.join(paths.thumbnails, f"{traits.collection_lower}_{item['ID']:03}_thumb.png")
                thumbnail.img.save(thumb_path)
                os.chmod(thumb_path, 0o777)
        elif composite.type == ImageType.ANIMATED:
            ext = os.path.splitext(composite.fp)[1]
            file_path = os.path.join(paths.images, f"{traits.collection_lower}_{item['ID']:03}{ext}")
            shutil.copyfile(composite.fp, file_path)
            os.chmod(file_path, 0o777)
            if traits.thumbnails:
                ext = os.path.splitext(thumbnail.fp)[1]
                thumb_path = os.path.join(paths.thumbnails, f"{traits.collection_lower}_{item['ID']:03}_thumb{ext}")
                shutil.copyfile(thumbnail.fp, thumb_path)
                os.chmod(thumb_path, 0o777)

        # print(f"Generated #{item['ID']:03}: {file_path}")
    return task_id

async def generate(paths: utils.Struct, traits: utils.Struct, batch: list, threaded: bool, machine_readable: bool):
    if threaded:
        semaphore = asyncio.Semaphore(4)   # Limit to 4 image building at once
    else:
        semaphore = asyncio.Semaphore(1)   # Limit to 1 images building at once by default
    async def sem_task(task):
        async with semaphore:
            return await task

    task_ids = [item['ID'] for item in batch]
    results = []

    if machine_readable:    # Make it more machine readable
        print(f"Generating {len(task_ids)} images...")
        for task in asyncio.as_completed( [sem_task(build_and_save_image(paths, traits, item, item['ID'])) for item in batch] ):
            result = await task
            results.append(result)
            task_ids.remove(result)
            print(f"Generated #{result:03} ({len(task_ids)} images remaining)")
            utils.set_progress_for_ui("Compositing the NFTs", len(results), len(results) + len(task_ids))
    else:   # Make it more human readable
        with yaspin.kbi_safe_yaspin().line as spinner:
            if len(task_ids) > 10:
                spinner.text = f"Generating {' '.join( [f'#{id:03}' for id in task_ids[:10]] )} (+ {len(task_ids) - 10} others)"
            else:
                spinner.text = f"Generating {' '.join( [f'#{id:03}' for id in task_ids] )}"
            for task in asyncio.as_completed( [sem_task(build_and_save_image(paths, traits, item, item['ID'])) for item in batch] ):
                result = await task
                results.append(result)
                task_ids.remove(result)
                if len(task_ids) > 10:
                    spinner.text = f"Generating {' '.join( [f'#{id:03}' for id in task_ids[:10]] )} (+ {len(task_ids) - 10} others)"
                else:
                    spinner.text = f"Generating {' '.join( [f'#{id:03}' for id in task_ids] )}"
                utils.set_progress_for_ui("Compositing the NFTs", len(results), len(results) + len(task_ids))

    return results

def main():
    # check for command line arguments
    args = parse_args()

    # Load traits.json
    traits = utils.load_traits(args.name)

    # Generate paths
    paths = utils.generate_paths(traits)

    # Remove directories if asked to
    make_directories(paths, traits, args.empty)

    # Define amount of images to generate
    total_image = args.count

    if total_image > utils.get_variation_cnt(traits.image_layers):
        sys.exit(f"count ({total_image}) cannot be greater than the number of variations ({utils.get_variation_cnt(traits.image_layers)})")

    # Set starting ID
    starting_id = args.id
    print("Starting at ID: " + str(starting_id))

    # Randomness seed in order of priority: traits.json, random seed
    if args.seed is None and traits.seed is not None and traits.seed != "":
        args.seed = str(traits.seed)
    if args.seed is None:
        timestamp = time.time_ns().to_bytes(16, byteorder='big')
        args.seed = b64encode(timestamp).decode("utf-8") # Encode timestamp to a base64 string
    print(f"Using randomness seed: {args.seed}")

    ## Generate Traits
    # Check if all-traits.json exists
    if os.path.exists(paths.all_traits):
        print("Previous batches exist, pulling in their data.")
        with open(paths.all_traits, 'r') as f:
            prev_batches = []
            # Remove IDs that will get replaced
            seen = set(range(starting_id, starting_id + total_image))
            for img in json.load(f):    # Keep only IDs not being re-generated
                if img["ID"] not in seen:
                    seen.add(img["ID"])
                    prev_batches.append(img)

    else:
        prev_batches = []

    ## Generate folders and names list from layers available in traits
    first_layer = 0 if traits.background_color else 1
    for i, l in enumerate(traits.image_layers):
        l["type"] = "filenames" if "filenames" in l else "rgba"
        l["names"] = list(l[l["type"]].keys())

        l["path"] = os.path.join(paths.source, f"layer{(first_layer + i):02}")

    # Generate the unique combinations based on layer weightings
    img_gen = ImageGenerator(layers=traits.image_layers, seed=args.seed, prev_batches=prev_batches, dup_cnt_limit=utils.get_variation_cnt(traits.image_layers))
    this_batch = img_gen.generate_images(starting_id=starting_id, image_cnt=total_image)

    all_images = prev_batches
    all_images.extend(this_batch)

    all_images.sort(key=ImageGenerator.sortID)

    # Double check that all images are unique to the whole collection
    if not all_images_unique(all_images):
        print(f"Some images are not unique, aborting")
        sys.exit(0)

    # Get Trait Counts
    print("How many of each trait exist?")

    for l in traits.image_layers:
        l["count"] = {item: 0 for item in l["names"]}

    for image in all_images:
        n = 1
        for l in traits.image_layers:
            item = image[l["layer_name"]]
            if not item in l["count"]:
                l["count"][item] = 0
            l["count"][item] += 1

    for i, l in enumerate(traits.image_layers):
        print(f"Layer {i:02}: {l['count']}")

    ## Store trait counts to json
    with open(paths.gen_stats, 'w') as outfile:
        gen_stats = {l["layer_name"]: l["count"] for l in traits.image_layers}
        gen_stats['seed'] = args.seed
        json.dump(gen_stats, outfile, indent=4)

    #### Generate Metadata for all Traits
    with open(paths.all_traits, 'w') as outfile:
        json.dump(all_images, outfile, indent=4)

    #### Generate Images
    composites = asyncio.run(generate(paths, traits, this_batch, args.threaded, args.php))
    print(f"Generated {len(this_batch)} images!")

    print("Look in " + paths.all_traits + " for an overview of all generated IDs and traits.")

if __name__ == "__main__":
    main()