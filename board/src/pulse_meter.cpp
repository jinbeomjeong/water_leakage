#include "../header/pulse_meter.h"
#include <ArduinoRS485.h>


static const unsigned long pulse_meter_baudrate = 9600;  // unit: bps
static const uint8_t pulse_meter_unit_address = 1;
static const uint8_t read_input_registers_function = 0x04;
static const uint8_t exception_function_flag = 0x80;
static const uint16_t pv_start_address = 0x03E9;  // protocol address of register 301002
static const uint16_t pv_register_count = 3;  // pv low word, pv high word, dot
static const uint8_t max_decimal_places = 4;
static const size_t request_frame_size = 8;
static const size_t response_frame_size = 3 + 2*pv_register_count + 2;  // header, registers, crc
static const size_t exception_frame_size = 5;  // unit address, function, exception code, crc
static const unsigned long response_timeout = 200;  // unit: ms
static const float power_of_ten[max_decimal_places+1] = {1.0f, 10.0f, 100.0f, 1000.0f, 10000.0f};


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


static void send_read_pv_request()
{
    uint8_t request[request_frame_size] = {pulse_meter_unit_address, read_input_registers_function,
                                           highByte(pv_start_address), lowByte(pv_start_address),
                                           highByte(pv_register_count), lowByte(pv_register_count), 0, 0};

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

    // drop the transmitted frame if the transceiver echoes it, the device answers only after its response wait time
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


void begin_pulse_meter()
{
    RS485.begin(pulse_meter_baudrate, SERIAL_8N2);
    RS485.receive();
}


PulseMeterStatus read_pulse_meter_pv(PulseMeterReading &reading)
{
    uint8_t response[response_frame_size];

    send_read_pv_request();
    const size_t response_size = receive_response(response);

    if (response_size == 0)
    {
        return PulseMeterStatus::timeout;
    }

    if (!check_response_crc(response, response_size))
    {
        return PulseMeterStatus::crc_error;
    }

    if (response[0] != pulse_meter_unit_address)
    {
        return PulseMeterStatus::invalid_response;
    }

    if (response[1] == (read_input_registers_function | exception_function_flag))
    {
        reading.exception_code = response[2];

        return PulseMeterStatus::exception_response;
    }

    if (response[1] != read_input_registers_function || response[2] != 2*pv_register_count)
    {
        return PulseMeterStatus::invalid_response;
    }

    // each register is big endian
    const uint16_t pv_low_word = (response[3] << 8) | response[4];
    const uint16_t pv_high_word = (response[5] << 8) | response[6];
    const uint16_t decimal_places = (response[7] << 8) | response[8];

    if (decimal_places > max_decimal_places)
    {
        return PulseMeterStatus::invalid_response;
    }

    // the manual does not define the word order, low word first was found by measurement on the device
    // unverified assumption: the manual does not define negative values and none has been measured,
    // 32-bit two's complement is assumed for the documented range of -19999 to 99999
    reading.raw_pv = static_cast<int32_t>((static_cast<uint32_t>(pv_high_word) << 16) | pv_low_word);
    reading.decimal_places = decimal_places;
    reading.pv = reading.raw_pv/power_of_ten[decimal_places];

    return PulseMeterStatus::ok;
}


const char *get_pulse_meter_status_text(PulseMeterStatus status)
{
    switch (status)
    {
        case PulseMeterStatus::ok:
            return "ok";

        case PulseMeterStatus::timeout:
            return "timeout";

        case PulseMeterStatus::crc_error:
            return "crc_error";

        case PulseMeterStatus::exception_response:
            return "exception_response";

        case PulseMeterStatus::invalid_response:
            return "invalid_response";
    }

    return "unknown";
}
