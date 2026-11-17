# Deviations from the original

Each entry is a settled decision. Don't change a deviated behaviour unless the user brings it up.

## Steering uses the left and right arrow keys instead of tilt

- Original: the ship is steered by tilting the device. The accelerometer is sampled every 0.2 seconds. acceleration.x values between -0.04 and 0.04 count as zero. Each frame the ship moves by accelX * (W / Global.getSpeed()), and the movement state changes (left, right, stopped) when accelX goes past 0.05 or -0.05.
- Changed: holding the right arrow key feeds a fixed positive accelX and holding the left arrow key feeds the same value negated. With neither held, accelX is 0. Everything downstream of accelX (movement state, the move and stabilise calls, talking movement, clamping, the listener update) stays as in the original.
- Reason: a Windows PC has no accelerometer. Decided by the user on 2026-11-17.
- Open detail: the fixed accelX magnitude isn't chosen yet. It has to be above 0.05 so the movement state changes. It gets tuned during testing and recorded here once settled.
