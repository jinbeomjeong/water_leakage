// otaa credentials of this board, copy this file to lorawan_keys.h and fill in the values from the network server
// lorawan_keys.h is ignored by git because the app key is a secret
#ifndef LORAWAN_KEYS_H
#define LORAWAN_KEYS_H

#include <Arduino.h>


// all values are written most significant byte first, the same order the network server shows
static uint8_t lorawan_dev_eui[8] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
static uint8_t lorawan_join_eui[8] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};  // also called app eui
static uint8_t lorawan_app_key[16] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};

#endif
