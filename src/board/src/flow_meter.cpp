#include "../header/flow_meter.h"
#include <ArduinoRS485.h>


static const unsigned long flow_meter_baudrate = 9600;  // unit: bps, comm set baud rate
// the manual does not give data bits, parity or stop bits, 8N1 was found on the device (8N2 and 8E1 gave broken bytes)
static const uint16_t flow_meter_serial_config = SERIAL_8N1;
static const uint8_t flow_meter_unit_address = 1;  // comm set comm id
static const uint8_t read_holding_registers_function = 0x03;
static const uint8_t exception_function_flag = 0x80;
// volume rate is registers 40005 and 40006 (manual p.18), protocol address 0x0004 as usual for modbus (40001 is 0x0000)
// found on the device: 0x0004 gives a valid response, 0x0005 runs past the register map and returns a malformed frame
static const uint16_t rate_start_address = 0x0004;
static const uint16_t rate_register_count = 2;
static const size_t rate_data_size = 2*rate_register_count;  // unit: byte, one ieee 754 float
// position of each float byte, most significant first, in the received data bytes
// the manual calls the data "4321 swapped fp", but the device sends plain big endian:
// data 3FD47AE1 reads as 1.66 in this order and as -2.9e20 with the bytes reversed
static const uint8_t float_byte_index[rate_data_size] = {0, 1, 2, 3};
static const size_t request_frame_size = 8;
static const size_t response_frame_size = 3 + rate_data_size + 2;  // header, registers, crc
static const size_t exception_frame_size = 5;  // unit address, function, exception code, crc
static const unsigned long response_timeout = 200;  // unit: ms


static uint16_t calculate_crc16(const uint8_t *frame, size_t frame_size)
{
    uint16_t crc = 0xFFFF;

    for (size_t i = 0; i < frame_size; i++)
    {
        crc ^= frame[i];

        for (uint8_t bit = 0; bit < 8; bit++)
        {
            if (crc & 0x0001)
            {
                crc = (crc >> 1) ^ 0xA001;
            }
            else
            {
                crc >>= 1;
            }
        }
    }

    return crc;
}


static void clear_receive_buffer()
{
    while (RS485.available() > 0)
    {
        RS485.read();
    }
}


static void send_read_rate_request()
{
    uint8_t request[request_frame_size] = {flow_meter_unit_address, read_holding_registers_function,
                                           highByte(rate_start_address), lowByte(rate_start_address),
                                           highByte(rate_register_count), lowByte(rate_register_count), 0, 0};

    // modbus sends the crc low byte first
    const uint16_t crc = calculate_crc16(request, request_frame_size-2);
    request[6] = lowByte(crc);
    request[7] = highByte(crc);

    clear_receive_buffer();
    RS485.noReceive();
    RS485.beginTransmission();
    RS485.write(request, request_frame_size);
    RS485.endTransmission();
    RS485.receive();

    // drop the transmitted frame if the transceiver echoes it
    clear_receive_buffer();
}


static size_t receive_response(uint8_t *response)
{
    size_t expected_size = response_frame_size;
    size_t received_size = 0;
    const unsigned long start_time = millis();

    while (received_size < expected_size && millis() - start_time < response_timeout)
    {
        if (RS485.available() > 0)
        {
            response[received_size++] = RS485.read();

            // an exception response is shorter than a normal response
            if (received_size == 2 && (response[1] & exception_function_flag))
            {
                expected_size = exception_frame_size;
            }
        }
        else
        {
            delay(1);
        }
    }

    return received_size == expected_size ? received_size : 0;
}


static bool check_response_crc(const uint8_t *response, size_t response_size)
{
    const uint16_t received_crc = response[response_size-2] | (response[response_size-1] << 8);

    return calculate_crc16(response, response_size-2) == received_crc;
}


static float convert_to_float(const uint8_t *data)
{
    uint32_t bits = 0;

    for (size_t i = 0; i < rate_data_size; i++)
    {
        bits = (bits << 8) | data[float_byte_index[i]];
    }

    float value;
    memcpy(&value, &bits, sizeof(value));

    return value;
}


void begin_flow_meter()
{
    RS485.begin(flow_meter_baudrate, flow_meter_serial_config);
    RS485.receive();
}


FlowMeterStatus read_flow_meter_rate(FlowMeterReading &reading)
{
    uint8_t response[response_frame_size];

    // register data stays zero unless a well formed response arrives
    memset(reading.register_data, 0, rate_data_size);

    send_read_rate_request();
    const size_t response_size = receive_response(response);

    if (response_size == 0)
    {
        return FlowMeterStatus::timeout;
    }

    if (!check_response_crc(response, response_size))
    {
        return FlowMeterStatus::crc_error;
    }

    if (response[0] != flow_meter_unit_address)
    {
        return FlowMeterStatus::invalid_response;
    }

    if (response[1] == (read_holding_registers_function | exception_function_flag))
    {
        reading.exception_code = response[2];

        return FlowMeterStatus::exception_response;
    }

    if (response[1] != read_holding_registers_function || response[2] != rate_data_size)
    {
        return FlowMeterStatus::invalid_response;
    }

    memcpy(reading.register_data, &response[3], rate_data_size);
    reading.flow_rate = convert_to_float(reading.register_data);

    if (!isfinite(reading.flow_rate))
    {
        return FlowMeterStatus::invalid_response;
    }

    return FlowMeterStatus::ok;
}


const char *get_flow_meter_status_text(FlowMeterStatus status)
{
    switch (status)
    {
        case FlowMeterStatus::ok:
            return "ok";

        case FlowMeterStatus::timeout:
            return "timeout";

        case FlowMeterStatus::crc_error:
            return "crc_error";

        case FlowMeterStatus::exception_response:
            return "exception_response";

        case FlowMeterStatus::invalid_response:
            return "invalid_response";
    }

    return "unknown";
}
