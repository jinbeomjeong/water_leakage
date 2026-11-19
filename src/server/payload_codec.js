// ChirpStack v4 payload codec for the water leakage board.
// Paste this file into Device profile > Codec > JavaScript functions.
//
// Uplink on FPort 1 is a sequence of records, multi-byte values are big endian
// (see build_uplink_payload in src/board/board.ino).
// Each record starts with one byte: sensor type in the upper 4 bits, status in the lower 4 bits.
//   type 0x0 flow:    1 data byte,  raw 0..200,  flow_lpm = raw * 0.1
//   type 0x1 current: 2 data bytes, raw 0..600,  current_ma = raw * 0.1 - 30
//   status 0x0 normal, 0x1 fault (data bytes are 0 and ignored)

var UPLINK_FPORT = 1;
var STATUS_NAMES = ["normal", "fault"];

var SENSORS = {
  0: { name: "flow", dataSize: 1, valueKey: "flow_lpm", toValue: function (raw) { return raw * 0.1; } },
  1: { name: "current", dataSize: 2, valueKey: "current_ma", toValue: function (raw) { return raw * 0.1 - 30; } }
};

function readUintBigEndian(bytes, offset, size) {
  var value = 0;
  for (var i = 0; i < size; i++) {
    value = value * 256 + bytes[offset + i];
  }
  return value;
}

function roundToTenth(value) {
  // keep one decimal place so 0.1 steps do not show floating point noise
  return Math.round(value * 10) / 10;
}

function decodeUplink(input) {
  var bytes = input.bytes;

  if (input.fPort !== UPLINK_FPORT) {
    return { errors: ["unexpected fPort " + input.fPort] };
  }
  if (bytes.length === 0) {
    return { errors: ["empty payload"] };
  }

  var data = {};
  var offset = 0;

  while (offset < bytes.length) {
    var header = bytes[offset];
    var sensorType = header >> 4;
    var statusCode = header & 0x0f;
    var sensor = SENSORS[sensorType];

    if (!sensor) {
      return { errors: ["unknown sensor type " + sensorType + " at byte " + offset] };
    }
    if (offset + 1 + sensor.dataSize > bytes.length) {
      return { errors: [sensor.name + " record at byte " + offset + " is truncated"] };
    }
    if (data[sensor.name + "_status"] !== undefined) {
      return { errors: ["duplicate " + sensor.name + " record at byte " + offset] };
    }

    var status = STATUS_NAMES[statusCode] || "unknown";
    data[sensor.name + "_status"] = status;

    if (status === "normal") {
      var raw = readUintBigEndian(bytes, offset + 1, sensor.dataSize);
      data[sensor.name + "_raw"] = raw;
      data[sensor.valueKey] = roundToTenth(sensor.toValue(raw));
    }

    offset += 1 + sensor.dataSize;
  }

  return { data: data };
}
