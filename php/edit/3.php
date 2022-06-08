<?php

    $collection_lower = $_GET['collection'];
    $traits_file = file_get_contents("./collections/${collection_lower}/config/traits.json");
    $tmp_traits_file = file_get_contents("./collections/${collection_lower}/config/traits.tmp.json");
    $traits = json_decode($traits_file, true);
    $tmp_traits = json_decode($tmp_traits_file, true);
    $s = 1;
    $t_display = $tmp_traits['trait_count'];

    if (!empty($tmp_traits) and $redirect !== "TRUE") { ?>
        <h3>Collection Info</h3>
        <div id="guide">
            <section>
                <p>STEP 03 - Define filenames, colors and rarities for each variation.</p>
                <p><b>Collection Name</b>: <?php echo $tmp_traits['collection_name'] ?></p>
                <?php if (array_key_exists('artist_name', $tmp_traits)) {
                    echo "<p><b>Artist's Name</b>: " . $tmp_traits['artist_name'] . "</p>";
                } ?>
                <?php if (array_key_exists('royalty_address', $tmp_traits)) {
                    echo "<p><b>Royalty Address</b>: " . $tmp_traits['royalty_address'] . "</p>";
                } ?>
                <?php if ($tmp_traits['background_color'] === true) {
                    echo "<p><b>Generate Background Colors</b>: YES</p>";
                    $s = 0;
                    $t_display = $t_display + 1;
                } ?>
                <p><b>Total Traits</b>: <?php echo $t_display ?></p>
            </section>
        </div>
        <form enctype="multipart/form-data" method="post" action="/edit/3?collection=<?php echo $collection_lower; ?>">
            <?php $t = 0;
            while ($s <= $tmp_traits['trait_count']) {
                $rarity_options = [
                    ['value' => 50, 'text' => 'Common'],
                    ['value' => 25, 'text' => 'Uncommon'],
                    ['value' => 10, 'text' => 'Rare'],
                    ['value' => 5 , 'text' => 'Epic'],
                    ['value' => 4 , 'text' => 'Legendary'],
                    ['value' => 3 , 'text' => 'Mythical'],
                    ['value' => 2 , 'text' => 'Transcendent'],
                    ['value' => 1 , 'text' => 'Godlike'],
                ];
                if ($t == 0 and $tmp_traits['background_color'] === true) {
                    unset($layer);
                    if (($traits['background_color'] === true) and isset($traits['image_layers'][$s])) {
                        $layer = $traits["image_layers"][$s];
                    } ?>
                    <h3 class="trait-title">Setup Background Colors:</h3>
                    <?php $v = 1; while ($v <= $layer['variations']) {
                        $trait_var = $s . "_" . $v;
                        unset($var_name);
                        if (isset($layer) and isset($layer['weights'][$v - 1])) {
                            $var_name = array_keys($layer['rgba'])[$v - 1];
                            $rgb = array_slice($layer['rgba'][$var_name], 0, 3);
                            $color_hex = '#' . implode('', array_map(function ($element) {
                                return sprintf('%02X', $element);
                            }, $rgb));
                            $opacity = $layer['rgba'][$var_name][3];
                        } ?>
                        <h4>Color #<?php echo $v ?>:</h4>
                        <div data-tooltip="Display Name: The pretty name of this variation">
                            <input required type="text" class="form wide" id="trait<?php echo $trait_var ?>_name" name="trait<?php echo $trait_var ?>_name" placeholder="Color Display Name" value="<?php echo isset($var_name) ? $var_name : null; ?>" />
                        </div>
                        <div class="trait-row wide">
                            <div class="trait-row" data-tooltip="Rarity: How rare this variation is">
                                <label for="trait<?php echo $trait_var ?>_weight">Rarity:&nbsp;&nbsp;</label>
                                <select required class="form" id="trait<?php echo $trait_var ?>_weight" name="trait<?php echo $trait_var ?>_weight" >
                                    <?php
                                    foreach ($rarity_options as $option) {
                                        $selected = (isset($var_name) and $layer['weights'][$v - 1] === $option['value']) ? 'selected' : null;
                                        echo "<option ".$selected." value=".$option['value'].">".$option['text']."</option>";
                                    }
                                    ?>
                                </select>
                            </div>
                            <div class="trait-row" data-tooltip="Color: The fill color of this background variation">
                                <label for="trait<?php echo $trait_var ?>_r">Color:&nbsp;&nbsp;</label>
                                <input required type="color" class="form small" id="trait<?php echo $trait_var ?>_color" name="trait<?php echo $trait_var ?>_color" value="<?php echo isset($var_name) ? $color_hex : null; ?>" />
                            </div>
                            <div class="trait-row small" data-tooltip="Opacity: The transparency of this background variation (0: invisible, 255: opaque)">
                                <label for="trait<?php echo $trait_var ?>_a">Opacity:&nbsp;&nbsp;</label>
                                <input required type="number" class="form number" id="trait<?php echo $trait_var ?>_alpha" min="0" max="255" name="trait<?php echo $trait_var ?>_alpha" placeholder="0-255" value="<?php echo isset($var_name) ? $opacity : null; ?>" />
                            </div>
                        </div>
                    <?php $v = $v + 1; }
                } else {
                    $s_offset = 0;
                    if ($traits['background_color'] === true and $tmp_traits['background_color'] === false) { $s_offset = 1; }
                    else if ($traits['background_color'] === false and $tmp_traits['background_color'] === true) { $s_offset = -1; }
                    unset($layer);
                    if (isset($traits['image_layers'][$s + $s_offset])) {
                        $layer = $traits["image_layers"][$s + $s_offset];
                    } ?>
                    <h3 class="trait-title">Setup "<?php echo $tmp_traits['image_layers'][$t]['layer_name']; ?>" Trait:</h3>
                    <?php $v = 1; while ($v <= $tmp_traits['image_layers'][$t]['variations']) {
                        $trait_var = $s . "_" . $v;
                        unset($var_name);
                        if (isset($layer) and isset($layer['weights'][$v - 1])) {
                            $var_name = array_keys($layer['filenames'])[$v - 1];
                            $filename = $layer['filenames'][$var_name];
                        } ?>
                        <h4>Variation #<?php echo $v ?>:</h4>
                        <div data-tooltip="Display Name: The pretty name of this variation">
                            <input required type="text" class="form wide" id="trait<?php echo $trait_var ?>_name" name="trait<?php echo $trait_var ?>_name" placeholder="Variation #<?php echo $v ?> Name" value="<?php echo isset($var_name) ? $var_name : null; ?>" />
                        </div>
                        <div class="trait-row wide">
                            <div data-tooltip="Rarity: How rare this variation is">
                                <label for="trait<?php echo $trait_var ?>_weight">Set Rarity:&nbsp;&nbsp;</label>
                                <select required class="form" id="trait<?php echo $trait_var ?>_weight" name="trait<?php echo $trait_var ?>_weight">
                                    <?php
                                    foreach ($rarity_options as $option) {
                                        $selected = (isset($var_name) and $layer['weights'][$v - 1] === $option['value']) ? 'selected' : null;
                                        echo "<option ".$selected." value=".$option['value'].">".$option['text']."</option>";
                                    }
                                    ?>
                                </select>
                            </div>
                            <div data-tooltip="Image: Choose the image file that should be used for this variation.">
                                <label for="trait<?php echo $trait_var ?>_r">Filename:&nbsp;&nbsp;</label>
                                <input required type="file" class="form med" id="trait<?php echo $trait_var ?>_file" name="trait<?php echo $trait_var ?>_file" />
                                <!-- <input required type="text" class="form med" id="trait<?php //echo $trait_var ?>_file" name="trait<?php //echo $trait_var ?>_file" value="<?php //echo isset($var_name) ? $filename : null; ?>" onclick="this.type='file'" oninput="this.type='file'" /> -->
                            </div>
                        </div>
                    <?php $v = $v + 1; }
                }
                $t = $t + 1;
                $s = $s + 1;
            } ?>
            <input type="hidden" name="redirect" id="redirect" value="TRUE" />
            <input class="form btn" type="submit" name="submit" value="FINISH" />
        </form>
    <?php } else if (!empty($tmp_traits) and $redirect === "TRUE") {
        $t = 0;
        if ($tmp_traits['background_color'] === true) { $s = 0; } else { $s = 1; }
        while ($s <= $tmp_traits['trait_count']) {
            $target_dir = "./collections/" . $tmp_traits['collection_lower'] . "/config/source_layers/layer" . sprintf('%02d', $s);;
            if (!file_exists($target_dir)) {
                mkdir($target_dir, 0755, true);
            }
            if ($t == 0 and $tmp_traits['background_color'] === true) {
                $v = 1;
                $tmp_traits["image_layers"][$t]['rgba'] = array();
                $tmp_traits["image_layers"][$t]['weights'] = array();
                while ($v <= $tmp_traits['image_layers'][$t]['variations']) {
                    $trait_var = $s . "_" . $v;
                    $rgb = str_split(str_replace("#", "", $_POST["trait${trait_var}_color"]), 2);
                    $tmp_traits["image_layers"][$t]['rgba'][$_POST["trait${trait_var}_name"]] = array(hexdec($rgb[0]), hexdec($rgb[1]), hexdec($rgb[2]), (int)$_POST["trait${trait_var}_alpha"]);
                    array_push($tmp_traits["image_layers"][$t]['weights'], (int)$_POST["trait${trait_var}_weight"]);
                    $v = $v + 1;
                }
            } else {
                $v = 1;
                $tmp_traits["image_layers"][$t]['filenames'] = array();
                $tmp_traits["image_layers"][$t]['weights'] = array();
                while ($v <= $tmp_traits['image_layers'][$t]['variations']) {
                    $trait_var = $s . "_" . $v;
                    $tmp_traits["image_layers"][$t]['filenames'][$_POST["trait${trait_var}_name"]] = $_FILES["trait${trait_var}_file"]['name'];
                    array_push($tmp_traits["image_layers"][$t]['weights'], (int)$_POST["trait${trait_var}_weight"]);
                    $target_file = $target_dir . "/" . $_FILES["trait${trait_var}_file"]['name'];
                    move_uploaded_file($_FILES["trait${trait_var}_file"]['tmp_name'], $target_file);
                    $v = $v + 1;
                }
            }
            $t = $t + 1;
            $s = $s + 1;
        }
        $tmp_traits_json = json_encode($tmp_traits, JSON_UNESCAPED_SLASHES|JSON_PRETTY_PRINT);
        file_put_contents("./collections/${collection_lower}/config/traits.tmp.json", $tmp_traits_json);
        Redirect("/edit/finish?collection=${collection_lower}", false);
    } else {
        Redirect('/edit/1', false);
    }

?>