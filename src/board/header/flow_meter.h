// read the flow rate from a flownics ft-210 flow transmitter over modbus rtu
#ifndef FLOW_METER_H
#define FLOW_METER_H

#include <Arduino.h>


enum class FlowMeterStatus
{
    ok,
    timeout,             // no complete response within the response timeout
    crc_error,           // response crc does not match
    exception_response,  // device answered with a modbus exception
    invalid_response,    // unexpected unit address, function code, byte count or a value that is not a number
};


struct FlowMeterReading
{
    float flow_rate;          // volume rate, unit set on the device by total_unit and time base
    uint8_t register_data[4]; // data bytes of registers 40005 and 40006 in received order, for checking the byte order
    uint8_t exception_code;   // valid only when the status is exception_response
};


// start the rs485 interface, the serial settings must match the device comm set: 9600 bps, modbus rtu, id 1
void begin_flow_meter();

// read the flow rate once, the reading is valid only when the returned status is ok
FlowMeterStatus read_flow_meter_rate(FlowMeterReading &reading);

// get a short lowercase name of a status for log output
const char *get_flow_meter_status_text(FlowMeterStatus status);

#endif
