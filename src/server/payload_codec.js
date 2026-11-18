// ChirpStack v4 payload codec for the water leakage board.
// Paste this file into Device profile > Codec > JavaScript functions.
//
// Uplink on FPort 1, 7 bytes, multi-byte values are big endian
// (see build_uplink_payload in src/board/board.ino):
//   byte 0: pulse meter status
//   byte 1: decimal places, valid only when the status is ok
//   byte 2-5: raw pv as int32, valid only when the status is ok
//   byte 6: modbus exception code, valid only when the status is exception_response

var UPLINK_FPORT = 1;
var UPLINK_SIZE = 7;
var STATUS_NAMES = ["ok", "timeout", "crc_error", "exception_response", "invalid_response"];

function readInt32BigEndian(bytes, offset) {
  // "| 0" turns the unsigned result into a signed 32-bit value
  return ((bytes[offset] << 24) | (bytes[offset + 1] << 16) | (bytes[offset + 2] << 8) | bytes[offset + 3]) | 0;
}

function decodeUplink(input) {
  var bytes = input.bytes;

  if (input.fPort !== UPLINK_FPORT) {
    return { errors: ["unexpected fPort " + input.fPort] };
  }
  if (bytes.length !== UPLINK_SIZE) {
    return { errors: ["expected " + UPLINK_SIZE + " bytes, got " + bytes.length] };
  }

  var statusCode = bytes[0];
  var data = {
    status: STATUS_NAMES[statusCode] || "unknown",
    status_code: statusCode
  };

  if (data.status === "ok") {
    var decimalPlaces = bytes[1];
    var rawPv = readInt32BigEndian(bytes, 2);
    data.decimal_places = decimalPlaces;
    data.raw_pv = rawPv;
    data.pv = rawPv / Math.pow(10, decimalPlaces);
  }
  if (data.status === "exception_response") {
    data.exception_code = bytes[6];
  }

  return { data: data };
}
