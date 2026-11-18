// join a lorawan network over otaa in kr920 and send uplinks with the rak4631 sx1262 radio
#ifndef LORAWAN_LINK_H
#define LORAWAN_LINK_H

#include <Arduino.h>


enum class LorawanStatus
{
    ok,
    not_joined,         // no join accept yet, the uplink was not sent
    busy,               // the mac layer is still handling the previous uplink
    payload_too_large,  // payload is larger than the application buffer
    send_failed,        // the mac layer rejected the uplink
};


// start the radio and the mac layer and send the first join request, returns false if the radio could not start
bool begin_lorawan();

// true after a join accept was received
bool is_lorawan_joined();

// send a join request again when the previous join failed and the retry interval has passed, call it from loop()
void update_lorawan_join();

// send one unconfirmed uplink on the application port
LorawanStatus send_lorawan_uplink(const uint8_t *payload, uint8_t payload_size);

// get a short lowercase name of a status for log output
const char *get_lorawan_status_text(LorawanStatus status);

#endif
