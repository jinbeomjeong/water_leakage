// read the pulse meter over rs485 with the rak5802, print each value to the pc over usb and send it over lorawan
#include <Adafruit_TinyUSB.h>
#include "header/pulse_meter.h"
#include "header/lorawan_link.h"


static const unsigned long usb_baudrate = 115200;  // unit: bps
static const unsigned long io_power_settle_time = 300;  // unit: ms
static const unsigned long read_interval = 1000;  // unit: ms
static const unsigned long uplink_interval = 30000;  // unit: ms, short value for testing
static const uint8_t uplink_payload_size = 7;  // unit: byte

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


// payload layout, multi-byte values are big endian:
// byte 0: pulse meter status (0 ok, 1 timeout, 2 crc_error, 3 exception_response, 4 invalid_response)
// byte 1: decimal places, valid only when the status is ok
// byte 2-5: raw pv as int32, valid only when the status is ok
// byte 6: modbus exception code, valid only when the status is exception_response
static void build_uplink_payload(PulseMeterStatus status, const PulseMeterReading &reading, uint8_t *payload)
{
    const bool is_ok = status == PulseMeterStatus::ok;
    const uint32_t raw_pv = is_ok ? static_cast<uint32_t>(reading.raw_pv) : 0;

    payload[0] = static_cast<uint8_t>(status);
    payload[1] = is_ok ? reading.decimal_places : 0;
    payload[2] = raw_pv >> 24;
    payload[3] = raw_pv >> 16;
    payload[4] = raw_pv >> 8;
    payload[5] = raw_pv;
    payload[6] = status == PulseMeterStatus::exception_response ? reading.exception_code : 0;
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
