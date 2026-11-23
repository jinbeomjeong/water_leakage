// read the ft-210 flow transmitter over rs485 with the rak5802, print each value to the pc over usb and send it over lorawan
#include <Adafruit_TinyUSB.h>
#include "header/flow_meter.h"
#include "header/lorawan_link.h"


static const unsigned long usb_baudrate = 115200;  // unit: bps
static const unsigned long io_power_settle_time = 300;  // unit: ms
static const unsigned long read_interval = 500;  // unit: ms, the ft-210 updates its display every 250 ms
static const unsigned long uplink_interval = 30000;  // unit: ms, short value for testing
static const uint8_t uplink_payload_size = 2;  // unit: byte, one flow record

// first byte of a record: sensor type in the upper 4 bits, sensor status in the lower 4 bits
static const uint8_t sensor_type_flow = 0x0;
static const uint8_t sensor_type_current = 0x1;  // reserved, the board has no current input yet
static const uint8_t sensor_status_normal = 0x0;
static const uint8_t sensor_status_fault = 0x1;
static const float flow_raw_per_lpm = 100.0f;  // flow raw unit is 0.01 lpm
static const uint8_t max_flow_raw = 200;  // unit: 0.01 lpm, values above 2.00 lpm are clamped
static const uint8_t flow_rate_print_digits = 3;

static unsigned long last_read_time = 0;  // unit: ms
static unsigned long last_uplink_time = 0;  // unit: ms

static FlowMeterStatus last_status = FlowMeterStatus::timeout;
static FlowMeterReading last_reading = {};


static void print_register_data(const FlowMeterReading &reading)
{
    Serial.print(" data=");

    for (uint8_t i = 0; i < sizeof(reading.register_data); i++)
    {
        if (reading.register_data[i] < 0x10)
        {
            Serial.print('0');
        }
        Serial.print(reading.register_data[i], HEX);
    }
}


static void print_reading(FlowMeterStatus status, const FlowMeterReading &reading)
{
    if (status == FlowMeterStatus::ok)
    {
        Serial.print("flow=");
        Serial.print(reading.flow_rate, flow_rate_print_digits);
        print_register_data(reading);
        Serial.println();
        return;
    }

    Serial.print("error=");
    Serial.print(get_flow_meter_status_text(status));

    if (status == FlowMeterStatus::exception_response)
    {
        Serial.print(" code=");
        Serial.print(reading.exception_code);
    }
    else if (status == FlowMeterStatus::invalid_response)
    {
        // all zero unless the frame was well formed and only the value was not a number
        print_register_data(reading);
    }

    Serial.println();
}


// convert the flow rate to 0.01 lpm units with rounding and clamp it to 0..200
// the device must be set to total_unit liter and time base minute
static uint8_t get_flow_raw(const FlowMeterReading &reading)
{
    const float flow_raw = roundf(reading.flow_rate*flow_raw_per_lpm);

    if (flow_raw <= 0.0f)
    {
        return 0;
    }
    if (flow_raw >= max_flow_raw)
    {
        return max_flow_raw;
    }
    return static_cast<uint8_t>(flow_raw);
}


// flow record layout:
// byte 0: sensor type 0x0 in the upper 4 bits, status in the lower 4 bits (0x0 normal, 0x1 fault)
// byte 1: raw flow in 0.01 lpm (0..200), 0 when the status is fault
static void build_uplink_payload(FlowMeterStatus status, const FlowMeterReading &reading, uint8_t *payload)
{
    const bool is_normal = status == FlowMeterStatus::ok;
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

    begin_flow_meter();
    begin_lorawan();
}


void loop()
{
    update_lorawan_join();

    if (millis() - last_read_time >= read_interval)
    {
        last_read_time = millis();
        last_status = read_flow_meter_rate(last_reading);
        print_reading(last_status, last_reading);
    }

    if (is_lorawan_joined() && millis() - last_uplink_time >= uplink_interval)
    {
        last_uplink_time = millis();
        send_last_reading();
    }
}
