# Zephyr RTOS Domain Rules

<reconnaissance_targets>
<!-- EXECUTE BEFORE ANY CODE GENERATION -->

1. `find . -name "west.yml" -o -name "prj.conf" -o -name "*.overlay" -o -name "*.dts"`
2. `cat west.yml` — verify `manifest.projects[].revision` is pinned (tag/commit)
3. `cat prj.conf` [`cat debug.conf`] — audit CONFIG_ flags
4. `cat *.overlay` — verify DT_ALIAS usage
5. `cat CMakeLists.txt` — verify `find_package(Zephyr)` + `target_sources`
6. `find app/src -type f -name "*.c"` — locate existing modules

**BLOCKED**: Do not generate code until reconnaissance completes
</reconnaissance_targets>

---

## 1. Build & Environment (West)

**REQUIRE**: Pin Zephyr kernel revision (tag/commit) in `west.yml`.
**REQUIRE**: `west update` before every build — synchronize module state.
**FORBID**: In-tree development — application MUST be out-of-tree (T2 topology).
**REQUIRE**: Declare all module dependencies in `west.yml::manifest.projects[]`.

**west.yml minimum**:
```yaml
manifest:
  defaults: { remote: upstream, revision: v4.0.0 }
  projects:
    - name: zephyr; import: true
    - name: <app>; path: application
```

**Build commands**: `west build -b <board> application/` | `west build --pristine` | `west flash`

**VIOLATION**: Missing revision pin | skipping `west update` | modifying `zephyr/` directory

---

## 2. Hardware & Config (DTS/Kconfig)

### DeviceTree (Hardware)
**MANDATE**: `DT_ALIAS(name)` macro for ALL hardware access — never hardcode pins/addresses.
**REQUIRE**: Define hardware in `.overlay` or `.dts` — NEVER in C source.
**REQUIRE**: Use `&label` node references — raw addresses forbidden.

**Pattern**: DTS alias → `DT_ALIAS()` → `dt_` API
```dts
aliases: status-led = &led0;
led0: led@0 { gpios = <&gpio0 13 GPIO_ACTIVE_LOW>; }
```
```c
const struct gpio_dt_spec led = DT_ALIAS_GPIO_SPEC(status_led);
```

### Kconfig (prj.conf)
**REQUIRE**: Separate `prj.conf` (release) from `debug.conf` (development).
**REQUIRE**: Prefix all flags as `CONFIG_<SUBSYSTEM>_<FEATURE>`.
**FORBID**: Enabling unused subsystems — minimize footprint.

```kconfig
# prj.conf
CONFIG_GPIO=y
CONFIG_PM=y
CONFIG_PM_DEVICE=y
CONFIG_ZBUS=y

# debug.conf
CONFIG_LOG=y
CONFIG_LOG_DEFAULT_LEVEL=4
CONFIG_SHELL=y
```

**VIOLATION**: Hardcoded pins | DT config in C | missing CONFIG_ prefix

---

## 3. Architecture & RTOS

### ZBus vs MsgQ/FIFO (Communication Boundaries)
**ZBus**: 1-to-N state broadcasting (sensor → UI + Cloud + Logger).
**k_msgq/k_fifo**: 1-to-1 data pipelining (ISR → processing thread).
**FORBID**: Direct function calls between threads.

**ZBus pattern**:
```c
ZBUS_CHANNEL_DEFINE(sensor_data_ch);
zbus_chan_pub(&sensor_data_ch, &msg, sizeof(msg), K_MSEC(10));
ZBUS_LISTEN(sensor_data_ch) { /* consume */ }
```

**MsgQ pattern**:
```c
K_MSGQ_DEFINE(data_msgq, sizeof(msg_t), 16, 4);
k_msgq_put(&data_msgq, &msg, K_NO_WAIT);
k_msgq_get(&data_msgq, &msg, K_FOREVER);
```

### Work Queue (Low-Frequency Tasks)
**MANDATE**: `k_work_submit_to_queue(&k_sys_work_q, &work)` for ISR offload.
**MANDATE**: `system_workqueue` for tasks < 1Hz — never spawn dedicated threads.
**FORBID**: `k_thread_create()` for background tasks under 1Hz.

```c
static struct k_work sensor_work;
k_work_init(&sensor_work, sensor_handler);
k_work_submit_to_queue(&k_sys_work_q, &sensor_work);
```

### Static Allocation (Memory Safety)
**MANDATE**: `K_THREAD_DEFINE()` for ALL threads — compile-time allocation.
**MANDATE**: Static `K_MSGQ_DEFINE()` / `K_FIFO_DEFINE()` declarations.
**FORBID**: `k_thread_create()` with dynamic stack/heap allocation.
**FORBID**: `k_malloc()` outside dedicated memory pools.

```c
K_THREAD_DEFINE(sensor_tid, 2048, sensor_main, NULL, NULL, NULL, 5, 0, 0);
K_MSGQ_DEFINE(data_msgq, sizeof(msg_t), 16, 4);
K_FIFO_DEFINE(isr_fifo);
```

### Memory Pools (If Dynamic Required)
**REQUIRE**: `K_MEM_POOL_DEFINE()` for any dynamic allocation.
**FORBID**: Unbounded `k_malloc()` / `k_free()` in hot paths.

```c
K_MEM_POOL_DEFINE(sensor_pool, sizeof(sensor_t), 16, K_FOREVER);
void *buf = k_mem_pool_alloc(&sensor_pool, K_NO_WAIT);
```

### ISR-to-Thread Bridging
**MANDATE**: `k_fifo_put()` / `k_msgq_put()` in ISR — defer processing to thread.
**FORBID**: Blocking operations (`k_msleep`, `k_sem_take`) in ISR context.
**REQUIRE**: ISR execution < 50 cycles — queue-only pattern.

```c
// ISR: queue only
void sensor_isr(const struct device *dev) {
    data = k_mem_pool_alloc(&pool, K_NO_WAIT);
    data->val = read_reg(dev);
    k_fifo_put(&isr_fifo, data);
}
// Thread: process
while (1) { data = k_fifo_get(&isr_fifo, K_FOREVER); handle(data); }
```

**VIOLATION**: Dynamic threads | direct inter-thread calls | blocking in ISR | unbounded malloc

---

## 4. Power & Subsystems

### Power Management
**REQUIRE**: `CONFIG_PM=y` + `CONFIG_PM_DEVICE=y` in prj.conf.
**MANDATE**: Event-driven async via `k_poll()` — zero blocking polling.
**FORBID**: `k_msleep()` loops in power-critical paths.

```kconfig
CONFIG_PM=y
CONFIG_PM_DEVICE=y
CONFIG_PM_DEVICE_INIT_PRIORITY=50
```

```c
// CORRECT: k_poll for multi-event wait
k_poll_event_define(events[2], 2);
k_poll(events, 2, K_FOREVER);

// WRONG: blocking poll — NEVER
while (!flag) { k_msleep(100); }
```

### Serialization
**PREFER**: `zcbor` (TinyCBOR) — never JSON/Protobuf for embedded serialization.
**REQUIRE**: CDDL schema for type-safe encode/decode.
**USE**: Standard Socket API (`socket()`, `send()`, `recv()`) for networking.

```c
// CDDL: SensorData = { value: int, timestamp: uint64 }
zcbor_encode_SensorData(state, &msg);
zcbor_decode_SensorData(payload, len, &msg);
```

### Subsystems (Never Reinvent)
**REQUIRE**: Settings subsystem for persistent configuration.
**REQUIRE**: `LOG_MODULE_REGISTER()` — never `printf()`.
**REQUIRE**: Shell subsystem for debug CLI — never custom parsers.

```c
LOG_MODULE_REGISTER(app, LOG_LEVEL_DBG);
LOG_DBG("Sensor value: %d", val);

struct settings_handler conf = { .name = "app", .h_set = handler };
settings_register(&conf);
```

### Testing (Twister + ztest)
**MANDATE**: `ztest` framework with Twister — custom test harnesses forbidden.
**MANDATE**: Logic tests on `native_posix` before hardware targeting.
**REQUIRE**: Tests in `tests/unit/<test_name>/` with `twister.yaml`.

```c
ZTEST(sensor_suite, test_sensor_init) {
    zassert_equal(sensor_init(&data), 0, "init failed");
}
ZTEST_SUITE(sensor_suite, NULL, NULL, NULL, NULL, NULL);
```

```yaml
# twister.yaml
tests:
  tests.unit.sensor_test:
    platform_allow: [native_posix, native_posix_64]
    integration_platforms: [qemu_cortex_m3]
```

**VIOLATION**: Blocking polls | JSON usage | printf debugging | missing ztest coverage

<domain_constraints>
# ZEPHYR DOMAIN CONSTRAINTS (Ultra-Compressed)

**RECON**: `cat west.yml prj.conf *.overlay` → `ls app/src` — BEFORE coding

**BUILD**: Pin revision in west.yml | west update mandatory | T2 out-of-tree ONLY
**DTS**: DT_ALIAS mandatory | hardware in overlay NOT C | &label refs only
**KCONFIG**: prj.conf + debug.conf separate | CONFIG_ prefix | no unused subsystems
**ZBUS**: 1-to-N state broadcast (pub/sub) | ZBUS_CHANNEL_DEFINE | ZBUS_LISTEN
**MSGQ**: 1-to-1 data pipeline | k_msgq/k_fifo | ISR→thread bridge
**WORKQ**: k_work_submit_to_queue(&k_sys_work_q) | <1Hz tasks | NO dedicated threads
**MEMORY**: K_THREAD_DEFINE static | K_MEM_POOL_DEFINE if dynamic | NO unbounded malloc
**ISR**: k_fifo_put queue-only | <50 cycles | NO blocking (k_msleep/k_sem_take)
**POWER**: CONFIG_PM=y | k_poll event-driven | ZERO blocking polling loops
**SERIAL**: zcbor CBOR NOT JSON | CDDL schema mandatory | Socket API for network
**SUBSYS**: Settings persist | LOG_MODULE not printf | Shell not custom CLI
**TEST**: ztest + Twister mandatory | native_posix first | tests/unit/ structure

**FORBIDDEN**: In-tree code | unpinned west | hardcoded pins | dynamic threads | blocking ISR | k_msleep loops | JSON/Protobuf | printf | missing ztest
</domain_constraints>
