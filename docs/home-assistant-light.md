# Desk lamp light in Home Assistant

`homeassistant/desk_lamp.yaml` adds `light.desk_lamp`: a real Home Assistant light with on/off, brightness and color temperature. You can use it in scenes, dashboards, voice commands and automations. Underneath, it presses the Lumos buttons. The firmware is unchanged, so there is nothing to flash.

The Lumos buttons can't go in a scene, because a scene restores states and a button has none. Home Assistant hides buttons in the scene editor. That is why this light exists.

## The state is assumed

The lamp sends nothing back, so Home Assistant can't know its real state. The light shows what Home Assistant last told the lamp to do. That state is stored in two helpers:

- `input_boolean.desk_lamp_on` ("Desk lamp on (assumed)")
- `input_select.desk_lamp_mode` ("Desk lamp mode (assumed)")

**The light becomes wrong when something else changes the lamp:** the physical remote, the Lumos buttons in Home Assistant, a missed radio frame, or a power cut. To correct it, set the two helpers to match the lamp. Changing a helper sends nothing.

The Power button is a toggle. Because of that, a wrong on/off state inverts the light: "on" turns the lamp off. Fix the helper when that happens.

## Install

1. In Home Assistant, check that the Lumos buttons have the expected IDs. Go to Settings → Devices & services → Entities and search for "lumos". You should see `button.lumos_lamp_power`, `button.lumos_lamp_warm_50` and so on. If yours are different, edit the IDs in `desk_lamp.yaml`.
2. Copy `homeassistant/desk_lamp.yaml` to `/config/packages/desk_lamp.yaml` on Home Assistant. The File editor or Studio Code Server add-on works for this, or a Samba share.
3. In `/config/configuration.yaml`, enable packages. If a `homeassistant:` key already exists, add the line under it:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

4. Go to Developer tools → YAML → Check configuration, then restart Home Assistant.
5. Set the two helpers to match the lamp right now: on or off, and the closest mode.

`light.desk_lamp` is not attached to the Lumos device. In the scene editor, add it under **Entities**, not Devices.

## What the light does

| You ask for | Buttons pressed |
| --- | --- |
| On, while assumed off | Power |
| On, while assumed on | nothing |
| Off, while assumed on | Power |
| Off, while assumed off | nothing |
| A brightness or color temperature | Power first if assumed off, then one mode button |

The lamp has 7 modes, so the light snaps each request to the nearest one and then shows that mode:

| Brightness | Below 3500 K | 3500–4749 K | 4750 K and up |
| --- | --- | --- | --- |
| 76–100% | Warm 100% | Neutral 100% | Cool 100% |
| 26–75% | Warm 50% | Neutral 50% | Cool 50% |
| 1–25% | Night mode | Night mode | Night mode |

The light shows 3000 K, 4000 K and 5500 K for Warm, Neutral and Cool, and 10% (warm) for Night mode. If you change only one value, the other keeps its current setting. The relative buttons (Brightness up/down, Color warmer/cooler) are not used. They stay available as separate buttons, but pressing them doesn't update the light.

Requests run one at a time, with 1 s after each press (`press_gap_ms`). One press takes about 0.3 s on air. Requests made while the light is busy wait in a queue and run in order. While the Lumos board is offline the light shows as unavailable, and commands are not recorded as done.

## Checked in software, not yet on hardware

Using the package unchanged, Home Assistant 2026.11.1 was run with stand-in `button.lumos_lamp_*` entities, and every button press was recorded. These 43 checks passed:

- On, off and toggle press Power only when the assumed state differs.
- Brightness and color temperature requests press the right mode, from on and from off.
- Scenes: a saved scene restores the lamp, and re-applying a matching scene presses nothing.
- Three requests sent at the same time press Power only once.
- Fast slider changes are all applied, in order, at least 1 s apart.
- Changing the helpers by hand presses nothing.
- Nothing is pressed during Home Assistant startup.
- The light is unavailable when the board is offline or its Power button entity is missing.

`tests/test_ha_package_static.py` checks the safety rules on every test run.

**Hardware checks for the user.** Agents can't observe the lamp. Record the results in the [hardware test log](hardware-test-log.md) as H6:

1. Off → on and on → off from the light. Each should toggle once.
2. From off, set the light to Warm 50% directly. Does the lamp turn on and end in Warm 50%? If it turns on but misses the mode, raise `press_gap_ms`.
3. Brightness 10%: is that Night mode?
4. Build a scene in the scene editor's Live Edit, turn the lamp off, and apply the scene.
5. Warm 50%: is it really 50% brightness? This hasn't been confirmed by eye yet ([Remote buttons](radio-captures.md#remote-buttons)).
6. Do the mode buttons turn the lamp on from off? This isn't needed, since the light presses Power first, but it is useful to know.
