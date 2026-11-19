// read the pulse meter over rs485 with the rak5802, print each value to the pc over usb and send it over lorawan
#include <Adafruit_TinyUSB.h>
#include "header/pulse_meter.h"
#include "header/lorawan_link.h"


static const unsigned long usb_baudrate = 115200;  // unit: bps
static const unsigned long io_power_settle_time = 300;  // unit: ms
static const unsigned long read_interval = 1000;  // unit: ms
static const unsigned long uplink_interval = 30000;  // unit: ms, short value for testing
static const uint8_t uplink_payload_size = 2;  // unit: byte, one flow record

// first byte of a record: sensor type in the upper 4 bits, sensor status in the lower 4 bits
static const uint8_t sensor_type_flow = 0x0;
static const uint8_t sensor_type_current = 0x1;  // reserved, the board has no current input yet
static const uint8_t sensor_status_normal = 0x0;
static const uint8_t sensor_status_fault = 0x1;
static const int64_t max_flow_raw = 200;  // unit: 0.1 lpm, values above 20.0 lpm are clamped

static unsigned long last_read_time = 0;  // unit: ms
static unsigned long last_uplink_time = 0;  // unit: ms

static PulseMeterStatus last_status = PulseMeterStatus::timeout;
static PulseMeterReading last_reading = {};


static void print_reading(PulseMeterStatus status, const PulseMeterReading &reading)
{
    if (status == PulseMeterStatus::ok)
    {
        Serial.print("pv=");
        Serial.println(reading.pv, reading.decimal_places);
    }
    else
    {
        Serial.print("error=");
        Serial.print(get_pulse_meter_status_text(status));

        if (status == PulseMeterStatus::exception_response)
        {
            Serial.print(" code=");
            Serial.print(reading.exception_code);
        }

        Serial.println();
    }
}


// convert the pv to 0.1 lpm units with rounding and clamp it to 0..200
// the pv unit must be set to lpm on the pulse meter
static uint8_t get_flow_raw(const PulseMeterReading &reading)
{
    int64_t flow_raw = reading.raw_pv;

    if (reading.decimal_places == 0)
    {
        flow_raw *= 10;
    }
    else
    {
        int64_t divisor = 1;
        for (uint8_t i = 1; i < reading.decimal_places; i++)
        {
            divisor *= 10;
        }

        // round half up only for non-negative values, negative values are clamped to 0 below
        if (flow_raw > 0)
        {
            flow_raw = (flow_raw + divisor/2)/divisor;
        }
    }

    if (flow_raw < 0)
    {
        return 0;
    }
    if (flow_raw > max_flow_raw)
    {
        return static_cast<uint8_t>(max_flow_raw);
    }
    return static_cast<uint8_t>(flow_raw);
}


// flow record layout:
// byte 0: sensor type 0x0 in the upper 4 bits, status in the lower 4 bits (0x0 normal, 0x1 fault)
// byte 1: raw flow in 0.1 lpm (0..200), 0 when the status is fault
static void build_uplink_payload(PulseMeterStatus status, const PulseMeterReading &reading, uint8_t *payload)
{
    const bool is_normal = status == PulseMeterStatus::ok;
    const uint8_t sensor_status = is_normal ? sensor_status_normal : sensor_status_fault;

    payload[0] = (sensor_type_flow << 4) | sensor_status;
    payload[1] = is_normal ? get_flow_raw(reading) : 0;
}


static void send_last_reading()
{
    uint8_t payload[uplink_payload_size];
    build_uplink_payload(last_status, last_reading, payload);

    const LorawanStatus status = send_lorawan_uplink(payload, uplink_payload_size);

    Serial.print("uplink=");
    Serial.println(get_lorawan_status_text(status));
}


void setup()
{
    Serial.begin(usb_baudrate);

    // wb_io2 controls the 3v3_s supply of the io slot and stays on because the device response must also be received
    pinMode(WB_IO2, OUTPUT);
    digitalWrite(WB_IO2, HIGH);
    delay(io_power_settle_time);

    begin_pulse_meter();
    begin_lorawan();
}


void loop()
{
    update_lorawan_join();

    if (millis() - last_read_time >= read_interval)
    {
        last_read_time = millis();
        last_status = read_pulse_meter_pv(last_reading);
        print_reading(last_status, last_reading);
    }

    if (is_lorawan_joined() && millis() - last_uplink_time >= uplink_interval)
    {
        last_uplink_time = millis();
        send_last_reading();
    }
}
