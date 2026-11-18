// read measurements from an autonics mp5 series pulse meter over modbus rtu
#ifndef PULSE_METER_H
#define PULSE_METER_H

#include <Arduino.h>


enum class PulseMeterStatus
{
    ok,
    timeout,             // no complete response within the response timeout
    crc_error,           // response crc does not match
    exception_response,  // device answered with a modbus exception
    invalid_response,    // unexpected unit address, function code, byte count or decimal places
};


struct PulseMeterReading
{
    int32_t raw_pv;          // pv without the decimal point
    uint8_t decimal_places;  // value of the dot register, 0 to 4
    float pv;                // raw_pv / 10^decimal_places, unit configured on the device
    uint8_t exception_code;  // valid only when the status is exception_response
};


// start the rs485 interface, the serial settings must match the device: 9600 bps, 8 data bits, no parity, 2 stop bits
void begin_pulse_meter();

// read the present value once, reading is valid only when the returned status is ok
PulseMeterStatus read_pulse_meter_pv(PulseMeterReading &reading);

// get a short lowercase name of a status for log output
const char *get_pulse_meter_status_text(PulseMeterStatus status);

#endif
