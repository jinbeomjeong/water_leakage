#include "../header/lorawan_link.h"
#include "../header/lorawan_keys.h"
#include <LoRaWan-Arduino.h>


static const uint8_t app_port = 1;
static const uint8_t join_trials = 3;  // join requests per join attempt before the failed callback
static const unsigned long join_retry_interval = 60000;  // unit: ms
static const size_t app_buffer_size = 64;  // unit: byte, larger than the kr920 limit at the slowest data rate

static uint8_t app_buffer[app_buffer_size];
static lmh_app_data_t app_data = {app_buffer, 0, app_port, 0, 0};

// set by the lora task callbacks and read by loop()
static volatile bool is_joined = false;
static volatile bool is_join_failed = false;
static volatile unsigned long join_failed_time = 0;  // unit: ms


static void handle_joined()
{
    is_joined = true;
    is_join_failed = false;
    Serial.println("lorawan=joined");
}


static void handle_join_failed()
{
    is_join_failed = true;
    join_failed_time = millis();
    Serial.println("lorawan=join_failed");
}


static void handle_downlink(lmh_app_data_t *downlink)
{
    Serial.print("lorawan=downlink port=");
    Serial.print(downlink->port);
    Serial.print(" size=");
    Serial.println(downlink->buffsize);
}


static void handle_class_confirmed(DeviceClass_t device_class)
{
    Serial.print("lorawan=class ");
    Serial.println(static_cast<int>(device_class));
}


// kr920 has no duty cycle limit, korea uses listen before talk which the region code handles
static lmh_param_t lorawan_param = {LORAWAN_ADR_ON, DR_0, LORAWAN_PUBLIC_NETWORK, join_trials, TX_POWER_0, LORAWAN_DUTYCYCLE_OFF};

static lmh_callback_t lorawan_callbacks = {BoardGetBatteryLevel, BoardGetUniqueId, BoardGetRandomSeed,
                                           handle_downlink, handle_joined, handle_class_confirmed, handle_join_failed,
                                           nullptr, nullptr};


bool begin_lorawan()
{
    if (lora_rak4630_init() != 0)
    {
        Serial.println("lorawan=radio_init_failed");

        return false;
    }

    lmh_setDevEui(lorawan_dev_eui);
    lmh_setAppEui(lorawan_join_eui);
    lmh_setAppKey(lorawan_app_key);

    if (lmh_init(&lorawan_callbacks, lorawan_param, true, CLASS_A, LORAMAC_REGION_KR920) != LMH_SUCCESS)
    {
        Serial.println("lorawan=mac_init_failed");

        return false;
    }

    Serial.println("lorawan=joining");
    lmh_join();

    return true;
}


bool is_lorawan_joined()
{
    return is_joined;
}


void update_lorawan_join()
{
    if (is_joined || !is_join_failed || millis() - join_failed_time < join_retry_interval)
    {
        return;
    }

    is_join_failed = false;
    Serial.println("lorawan=joining");
    lmh_join();
}


LorawanStatus send_lorawan_uplink(const uint8_t *payload, uint8_t payload_size)
{
    if (!is_joined)
    {
        return LorawanStatus::not_joined;
    }

    if (payload_size > app_buffer_size)
    {
        return LorawanStatus::payload_too_large;
    }

    memcpy(app_buffer, payload, payload_size);
    app_data.buffsize = payload_size;
    app_data.port = app_port;

    switch (lmh_send(&app_data, LMH_UNCONFIRMED_MSG))
    {
        case LMH_SUCCESS:
            return LorawanStatus::ok;

        case LMH_BUSY:
            return LorawanStatus::busy;

        default:
            return LorawanStatus::send_failed;
    }
}


const char *get_lorawan_status_text(LorawanStatus status)
{
    switch (status)
    {
        case LorawanStatus::ok:
            return "ok";

        case LorawanStatus::not_joined:
            return "not_joined";

        case LorawanStatus::busy:
            return "busy";

        case LorawanStatus::payload_too_large:
            return "payload_too_large";

        case LorawanStatus::send_failed:
            return "send_failed";
    }

    return "unknown";
}
