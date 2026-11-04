// read the pulse meter over rs485 with the rak5802 and print each value to the pc over usb
#include <Adafruit_TinyUSB.h>
#include "header/pulse_meter.h"


static const unsigned long usb_baudrate = 115200;  // unit: bps
static const unsigned long io_power_settle_time = 300;  // unit: ms
static const unsigned long read_interval = 1000;  // unit: ms

static unsigned long last_read_time = 0;  // unit: ms


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


void setup()
{
    Serial.begin(usb_baudrate);

    // wb_io2 controls the 3v3_s supply of the io slot and stays on because the device response must also be received
    pinMode(WB_IO2, OUTPUT);
    digitalWrite(WB_IO2, HIGH);
    delay(io_power_settle_time);

    begin_pulse_meter();
}


void loop()
{
    if (millis() - last_read_time < read_interval)
    {
        return;
    }

    last_read_time = millis();

    PulseMeterReading reading;
    const PulseMeterStatus status = read_pulse_meter_pv(reading);

    print_reading(status, reading);
}
