# Algorithm Test Layout — Embedded Signal Processing Example

## Problem Domain

An embedded signal processing module with:

- Input: sampled data stream (e.g., ADC samples at 200 Hz)
- Processing: band-pass filter → peak detection → state machine → result output
- Output: heart rate estimate, peak events, state transitions

The hardware sampling and algorithm logic must be decoupled. The algorithm runs offline regression on `native_sim`. Real hardware tests verify only the sampling chain and actual data behavior.

---

## Recommended Directory Structure

```
src/
├── bcg_algo/                          # Algorithm code (hardware-independent)
│   ├── bcg_filter.c / .h             # Band-pass filter
│   ├── bcg_peak_detector.c / .h      # Peak detection
│   ├── bcg_state_machine.c / .h      # State machine
│   └── bcg_utils.h                   # Shared types and helpers
└── drivers/
    └── bcg_adc.c / .h                # Hardware ADC driver (NOT tested in native_sim)

tests/
├── bcg_filter/                        # Layer A: pure unit test
│   ├── CMakeLists.txt
│   ├── prj.conf
│   ├── testcase.yaml
│   └── src/
│       └── main.c
├── bcg_peak_detector/                 # Layer A: pure unit test
│   ├── CMakeLists.txt
│   ├── prj.conf
│   ├── testcase.yaml
│   └── src/
│       └── main.c
├── bcg_algo_pipeline/                 # Layer B: integration test
│   ├── CMakeLists.txt
│   ├── prj.conf
│   ├── testcase.yaml
│   ├── test_data/                    # Reference input/output files
│   │   ├── input_30s_200hz.bin
│   │   └── expected_peaks.bin
│   └── src/
│       └── main.c
└── bcg_adc_hardware/                  # Layer D: real hardware test
    ├── CMakeLists.txt
    ├── prj.conf
    ├── testcase.yaml
    └── src/
        └── main.c
```

---

## How to Inject Fixed Array Input

Define test data as `static const` arrays in the test source. No file I/O needed.

```c
/* 1 second of simulated BCG data at 200 Hz, with known peaks */
static const int16_t test_input[] = {
    /* 200 samples: flat baseline with two peaks at sample 50 and 150 */
    /* samples 0-49: baseline=1000 */
    1000, 1000, 1000, /* ... fill 50 values ... */
    /* samples 49-59: peak (triangular, amplitude=300) */
    1000, 1150, 1300, 1150, 1000, 1000, 1000, 1000, 1000, 1000,
    /* samples 60-149: baseline */
    1000, 1000, /* ... fill ... */
    /* samples 150-159: second peak */
    1000, 1150, 1300, 1150, 1000, 1000, 1000, 1000, 1000, 1000,
    /* samples 160-199: baseline */
    1000, 1000, /* ... fill ... */
};

#define TEST_SAMPLE_PERIOD_US 5000  /* 200 Hz */

ZTEST(bcg_peak_detector, test_known_peaks_detected)
{
    struct bcg_peak_detector det;
    bcg_peak_detector_init(&det);

    for (size_t i = 0; i < ARRAY_SIZE(test_input); i++) {
        uint32_t ts_us = (uint32_t)(i * TEST_SAMPLE_PERIOD_US);
        bcg_peak_detector_feed(&det, ts_us, test_input[i]);
    }

    struct bcg_peak_result result;
    bcg_peak_detector_get_result(&det, &result);

    zassert_equal(result.peak_count, 2, "expected 2 peaks, got %d",
                  result.peak_count);
    /* Peak at sample 50 -> timestamp 250000 us, +/- tolerance */
    zassert_within(result.peaks[0].timestamp_us, 250000, 10000,
                   "first peak timestamp out of range");
}
```

---

## How to Simulate Data Interruption

Feed samples with a timestamp gap to simulate dropped data or sensor disconnection.

```c
ZTEST(bcg_peak_detector, test_handles_data_gap)
{
    struct bcg_peak_detector det;
    bcg_peak_detector_init(&det);

    /* Feed 100 normal samples */
    for (int i = 0; i < 100; i++) {
        bcg_peak_detector_feed(&det, i * 5000, 1000);
    }

    /* Simulate 2-second gap (400 samples dropped at 200 Hz) */
    /* Continue with different amplitude to verify filter reset */
    for (int i = 0; i < 100; i++) {
        uint32_t ts_us = (uint32_t)((500 + i) * 5000);  /* jump from 100->500 */
        bcg_peak_detector_feed(&det, ts_us, 1000);
    }

    struct bcg_peak_result result;
    bcg_peak_detector_get_result(&det, &result);

    /* After a gap, the detector should either:
     * - Reset its state and continue cleanly, OR
     * - Flag the gap and mark the segment invalid
     * Adapt assertion to your module's contract. */
    zassert_true(result.gap_detected || result.state == DETECTOR_STATE_RESET,
                 "detector did not handle data gap");
}
```

---

## How to Test State Reset

Verify that `reset()` returns the module to a known initial state and that a fresh feed cycle produces correct results.

```c
ZTEST(bcg_state_machine, test_reset_returns_to_idle)
{
    struct bcg_state_machine sm;
    bcg_state_machine_init(&sm);

    /* Drive through multiple states */
    bcg_state_machine_feed(&sm, EVENT_START);
    bcg_state_machine_feed(&sm, EVENT_DATA_VALID);
    bcg_state_machine_feed(&sm, EVENT_DATA_VALID);
    zassert_equal(bcg_state_machine_get_state(&sm), STATE_RUNNING);

    /* Reset */
    bcg_state_machine_reset(&sm);
    zassert_equal(bcg_state_machine_get_state(&sm), STATE_IDLE);

    /* Verify a new cycle works identically */
    bcg_state_machine_feed(&sm, EVENT_START);
    zassert_equal(bcg_state_machine_get_state(&sm), STATE_RUNNING);
}

ZTEST(bcg_state_machine, test_reset_discards_accumulated_data)
{
    struct bcg_state_machine sm;
    bcg_state_machine_init(&sm);

    /* Accumulate partial result */
    for (int i = 0; i < 50; i++) {
        bcg_state_machine_feed(&sm, EVENT_DATA_VALID);
    }

    bcg_state_machine_reset(&sm);

    struct sm_result result;
    bcg_state_machine_get_result(&sm, &result);
    zassert_equal(result.sample_count, 0,
                  "reset did not clear accumulated data");
}
```

---

## How to Check Output Values and Tolerance

Always justify the tolerance value. Never use a magic number without explanation.

```c
ZTEST(bcg_filter, test_passband_response)
{
    struct bcg_filter filt;
    bcg_filter_init(&filt, &filter_config_200hz);

    /*
     * Feed a 1 Hz sine wave (in passband, 0.5-4 Hz).
     * Expected output amplitude: ~95% of input (passband gain ~-0.4 dB).
     *
     * Tolerance: +/-5% accounts for:
     *   - 16-bit fixed-point quantization (~0.3%)
     *   - Filter transient settling (first 200 samples discarded)
     *   - Window length spectral leakage (~1-2%)
     */
    const int16_t amplitude = 1000;
    int16_t max_output = INT16_MIN;

    for (int i = 0; i < 1000; i++) {
        /* Generate 1 Hz sine at 200 Hz sample rate */
        int16_t sample = (int16_t)(amplitude *
            sinf(2.0f * 3.14159f * 1.0f * i / 200.0f));
        int16_t out = bcg_filter_feed(&filt, sample);
        if (i >= 200) {  /* skip transient */
            max_output = MAX(max_output, out);
        }
    }

    int16_t expected = (int16_t)(amplitude * 0.95f);
    zassert_within(max_output, expected, expected * 5 / 100,
                   "passband gain outside expected range");
}
```

### Tolerance sources to document

| Source | Typical magnitude | How to determine |
|--------|-------------------|------------------|
| Fixed-point quantization | 0.1–1% | From bit depth: 1/2^(N-1) |
| Filter transient | Varies | Run with known input, measure settling time |
| Floating-point rounding | ~1e-7 | Usually negligible for 32-bit float |
| Algorithm approximation | Domain-specific | Compare to reference implementation |
| Timing jitter (real hardware) | 1–5% | Measure on hardware, not applicable to native_sim |

---

## How to Add Bug Regression Tests

Every fixed bug gets a regression test that would fail without the fix.

```c
/*
 * Regression: PR #142 — filter output saturated to INT16_MAX on
 * sustained DC offset input (amplitude > 80% of range).
 *
 * Root cause: accumulator overflow in IIR stage.
 * Fix: clamped accumulator to 32-bit range before output scaling.
 *
 * This test feeds a large DC offset for 10 seconds.
 * Without the fix, output saturates to INT16_MAX after ~2 seconds.
 */
ZTEST(bcg_filter, test_regression_pr142_dc_offset_no_saturation)
{
    struct bcg_filter filt;
    bcg_filter_init(&filt, &filter_config_200hz);

    bool saturated = false;

    for (int i = 0; i < 2000; i++) {  /* 10 seconds at 200 Hz */
        /* DC offset at 80% of int16 range */
        int16_t out = bcg_filter_feed(&filt, 26000);
        if (out >= INT16_MAX - 1 || out <= INT16_MIN + 1) {
            saturated = true;
            break;
        }
    }

    zassert_false(saturated,
                  "filter output saturated — regression of PR #142");
}
```

### Naming convention for regression tests

```
test_regression_<issue_id>_<short_description>
```

Examples:

- `test_regression_pr142_dc_offset_no_saturation`
- `test_regression_issue47_zero_length_input_crash`
- `test_regression_fw260528_peak_missed_after_gap`

---

## What Belongs in Real Hardware Tests (Layer D)

These **cannot** be verified on `native_sim` and must be tested on the actual board:

| Item | Why |
|------|-----|
| ADC sampling rate accuracy | Timer + DMA timing is hardware-dependent |
| ADC noise floor and ENOB | Real analog front-end noise |
| PGA gain accuracy | Requires calibrated signal source |
| DMA transfer correctness | EasyDMA behavior on nRF is silicon-specific |
| GPPI/TIMER trigger jitter | Hardware event timing |
| BLE data transport throughput | Radio and protocol stack behavior |
| Power consumption in each mode | Requires current measurement |
| Interrupt latency | Cortex-M NVIC timing on real silicon |
| Sensor data quality (SNR) | Requires physical signal source |
| End-to-end: sensor → ADC → filter → BLE → phone | System integration |

### Hardware test structure

The hardware test binary should:

1. Initialize the full peripheral chain (ADC, DMA, BLE)
2. Capture N seconds of data
3. Run the algorithm on captured data
4. Report results over BLE or RTT
5. Compare against expected bounds (not exact values — real data is noisy)

```
tests/bcg_adc_hardware/
├── CMakeLists.txt
├── prj.conf          # includes full peripheral config
├── testcase.yaml     # build_only: true (no Twister runner for RTT-only boards)
└── src/
    └── main.c        # init → capture → process → report
```

`testcase.yaml` for hardware tests:

```yaml
tests:
  bcg_adc_hardware.build:
    platform_allow:
      - nrf54l15dk/nrf54l15/cpuapp
    build_only: true
    tags:
      - hardware
      - bcg
```
