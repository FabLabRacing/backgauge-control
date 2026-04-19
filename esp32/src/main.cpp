#include <Arduino.h>

const int DEPTH_STEP_PIN  = 13;
const int DEPTH_DIR_PIN   = 14;
const int HEIGHT_STEP_PIN = 27;
const int HEIGHT_DIR_PIN  = 26;

struct AxisState {
    char id;
    int stepPin;
    int dirPin;
    float current;
    float commanded;
    bool moving;
    bool homed;
    String err;
};

AxisState depth  = {'D', DEPTH_STEP_PIN,  DEPTH_DIR_PIN,  0.0f, 0.0f, false, false, ""};
AxisState height = {'H', HEIGHT_STEP_PIN, HEIGHT_DIR_PIN, 0.0f, 0.0f, false, false, ""};

String rxLine;

AxisState* getAxis(char id) {
    if (id == 'D') return &depth;
    if (id == 'H') return &height;
    return nullptr;
}

void emitState(const AxisState& a) {
    Serial.printf(
        "STATE,%c,CUR=%.4f,CMD=%.4f,MOV=%d,HOMED=%d,ERR=%s\n",
        a.id,
        a.current,
        a.commanded,
        a.moving ? 1 : 0,
        a.homed ? 1 : 0,
        a.err.c_str()
    );
}

void emitAllStates() {
    emitState(depth);
    emitState(height);
}

void handleSetCmd(char axisId, const String& valueStr) {
    AxisState* axis = getAxis(axisId);
    if (!axis) {
        Serial.println("ERR,ALL,BAD_AXIS");
        return;
    }

    axis->commanded = valueStr.toFloat();
    Serial.printf("OK,SET_CMD,%c\n", axis->id);
    emitState(*axis);
}

void handleMove(char axisId) {
    AxisState* axis = getAxis(axisId);
    if (!axis) {
        Serial.println("ERR,ALL,BAD_AXIS");
        return;
    }

    float distance = axis->commanded - axis->current;

    if (fabs(distance) < 0.0005f) {
        Serial.printf("EVENT,%c,MOVE_DONE\n", axis->id);
        emitState(*axis);
        return;
    }

    int dir = (distance > 0) ? +1 : -1;

    digitalWrite(axis->dirPin, (dir > 0) ? HIGH : LOW);

    long steps = lroundf(fabs(distance) * 200.0f); // TEMP: 200 steps/unit

    Serial.printf("OK,MOVE,%c\n", axis->id);

    for (long i = 0; i < steps; i++) {
        digitalWrite(axis->stepPin, HIGH);
        delayMicroseconds(500);
        digitalWrite(axis->stepPin, LOW);
        delayMicroseconds(500);

        float stepDist = 1.0f / 200.0f;

        if (dir > 0)
            axis->current += stepDist;
        else
            axis->current -= stepDist;
    }

    axis->current = axis->commanded;

    Serial.printf("EVENT,%c,MOVE_DONE\n", axis->id);
    emitState(*axis);
}

void processCommand(String line) {
    line.trim();
    if (line.length() == 0) return;

    if (line == "PING") {
        Serial.println("OK,PING");
        return;
    }

    if (line == "STATUS?") {
        emitAllStates();
        return;
    }

    int p1 = line.indexOf(',');
    String cmd = (p1 < 0) ? line : line.substring(0, p1);
    cmd.trim();

    if (cmd == "SET_CMD") {
        int p2 = line.indexOf(',', p1 + 1);
        if (p1 < 0 || p2 < 0) {
            Serial.println("ERR,ALL,BAD_ARGS");
            return;
        }

        String axisStr = line.substring(p1 + 1, p2);
        String valueStr = line.substring(p2 + 1);
        axisStr.trim();
        valueStr.trim();

        if (axisStr.length() != 1) {
            Serial.println("ERR,ALL,BAD_AXIS");
            return;
        }

        handleSetCmd(axisStr[0], valueStr);
        return;
    }
    if (cmd == "MOVE") {
         if (p1 < 0) {
             Serial.println("ERR,ALL,BAD_ARGS");
            return;
        }

        String axisStr = line.substring(p1 + 1);
        axisStr.trim();

        if (axisStr.length() != 1) {
            Serial.println("ERR,ALL,BAD_AXIS");
            return;
        }

        handleMove(axisStr[0]);
        return;
    }
    Serial.println("ERR,ALL,UNKNOWN_CMD");
}


void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("OK,BOOT");
    emitAllStates();
    pinMode(DEPTH_STEP_PIN, OUTPUT);
    pinMode(DEPTH_DIR_PIN, OUTPUT);
    pinMode(HEIGHT_STEP_PIN, OUTPUT);
    pinMode(HEIGHT_DIR_PIN, OUTPUT);

    digitalWrite(DEPTH_STEP_PIN, LOW);
    digitalWrite(DEPTH_DIR_PIN, LOW);
    digitalWrite(HEIGHT_STEP_PIN, LOW);
    digitalWrite(HEIGHT_DIR_PIN, LOW);
}

void loop() {
    while (Serial.available()) {
        char c = (char)Serial.read();

        if (c == '\n') {
            processCommand(rxLine);
            rxLine = "";
        } else if (c != '\r') {
            rxLine += c;
        }
    }
}