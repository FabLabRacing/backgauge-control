#include <Arduino.h>

const int DEPTH_STEP_PIN  = 13;
const int DEPTH_DIR_PIN   = 14;
const int HEIGHT_STEP_PIN = 27;
const int HEIGHT_DIR_PIN  = 26;

const float STEPS_PER_UNIT = 200.0f;

const unsigned long STEP_PULSE_US = 200;
const unsigned long STEP_INTERVAL_US = 1000;
const unsigned long STATE_INTERVAL_US = 100000; // 100 ms


struct AxisState {
    char id;
    int stepPin;
    int dirPin;
    float current;
    float commanded;
    bool moving;
    bool homed;
    String err;

    int motionDir;
    long stepsRemaining;
    unsigned long lastStepMicros;
    unsigned long lastStateMicros;
    bool jogging;
};

AxisState depth;
AxisState height;

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

    if (axis->moving) {
        Serial.printf("ERR,%c,BUSY\n", axis->id);
        return;
    }

    float distance = axis->commanded - axis->current;

    if (fabs(distance) < 0.0005f) {
        Serial.printf("EVENT,%c,MOVE_DONE\n", axis->id);
        emitState(*axis);
        return;
    }

    int dir = (distance > 0) ? +1 : -1;
    long steps = lroundf(fabs(distance) * STEPS_PER_UNIT);

    if (steps <= 0) {
        axis->current = axis->commanded;
        Serial.printf("EVENT,%c,MOVE_DONE\n", axis->id);
        emitState(*axis);
        return;
    }

    axis->motionDir = dir;
    axis->stepsRemaining = steps;
    axis->lastStepMicros = micros();
    axis->moving = true;
    axis->lastStateMicros = micros();
    axis->err = "";
    axis->jogging = false;

    digitalWrite(axis->dirPin, (dir > 0) ? HIGH : LOW);

    Serial.printf("OK,MOVE,%c\n", axis->id);
    emitState(*axis);
}

void handleStop(const String& target) {
    if (target == "ALL") {
        depth.moving = false;
        depth.stepsRemaining = 0;
        depth.motionDir = 0;

        height.moving = false;
        height.stepsRemaining = 0;
        height.motionDir = 0;

        Serial.println("EVENT,ALL,STOPPED");
        emitAllStates();
        return;
    }

    if (target.length() != 1) {
        Serial.println("ERR,ALL,BAD_AXIS");
        return;
    }

    AxisState* axis = getAxis(target[0]);
    if (!axis) {
        Serial.println("ERR,ALL,BAD_AXIS");
        return;
    }

    axis->moving = false;
    axis->stepsRemaining = 0;
    axis->motionDir = 0;
    axis->jogging = false;

    Serial.printf("EVENT,%c,STOPPED\n", axis->id);
    emitState(*axis);
}


void serviceMove(AxisState& axis) {
    if (!axis.moving) {
        return;
    }

    unsigned long now = micros();

    if ((now - axis.lastStepMicros) < STEP_INTERVAL_US) {
        return;
    }

    axis.lastStepMicros = now;

    digitalWrite(axis.stepPin, HIGH);
    delayMicroseconds(STEP_PULSE_US);
    digitalWrite(axis.stepPin, LOW);

    float stepDist = 1.0f / STEPS_PER_UNIT;

    if (axis.motionDir > 0) {
        axis.current += stepDist;
    } else {
        axis.current -= stepDist;
    }

    if (axis.jogging) {
        axis.commanded = axis.current;

        if ((now - axis.lastStateMicros) >= STATE_INTERVAL_US) {
            axis.lastStateMicros = now;
            emitState(axis);
        }

        return;
    }

    axis.stepsRemaining--;

    if ((now - axis.lastStateMicros) >= STATE_INTERVAL_US) {
        axis.lastStateMicros = now;
        emitState(axis);
    }

    if (axis.stepsRemaining <= 0) {
        axis.current = axis.commanded;
        axis.moving = false;
        axis.motionDir = 0;
        Serial.printf("EVENT,%c,MOVE_DONE\n", axis.id);
        emitState(axis);
    }
}

void handleJogStart(char axisId, const String& sign) {
    AxisState* axis = getAxis(axisId);
    if (!axis) {
        Serial.println("ERR,ALL,BAD_AXIS");
        return;
    }

    if (axis->moving) {
        Serial.printf("ERR,%c,BUSY\n", axis->id);
        return;
    }

    int dir;
    if (sign == "+") {
        dir = +1;
    } else if (sign == "-") {
        dir = -1;
    } else {
        Serial.printf("ERR,%c,BAD_JOG_DIR\n", axis->id);
        return;
    }

    axis->motionDir = dir;
    axis->stepsRemaining = 0;
    axis->lastStepMicros = micros();
    axis->lastStateMicros = micros();
    axis->moving = true;
    axis->jogging = true;
    axis->err = "";

    digitalWrite(axis->dirPin, (dir > 0) ? HIGH : LOW);

    Serial.printf("OK,JOG_START,%c\n", axis->id);
    emitState(*axis);
}

void handleJogStop(const String& target) {
    if (target == "ALL") {
        depth.jogging = false;
        depth.moving = false;
        depth.motionDir = 0;
        depth.commanded = depth.current;

        height.jogging = false;
        height.moving = false;
        height.motionDir = 0;
        height.commanded = height.current;

        Serial.println("EVENT,ALL,JOG_STOPPED");
        emitAllStates();
        return;
    }

    if (target.length() != 1) {
        Serial.println("ERR,ALL,BAD_AXIS");
        return;
    }

    AxisState* axis = getAxis(target[0]);
    if (!axis) {
        Serial.println("ERR,ALL,BAD_AXIS");
        return;
    }

    if (!axis->jogging) {
        Serial.printf("OK,JOG_STOP,%c\n", axis->id);
        emitState(*axis);
        return;
    }

    axis->jogging = false;
    axis->moving = false;
    axis->motionDir = 0;
    axis->commanded = axis->current;

    Serial.printf("EVENT,%c,JOG_STOPPED\n", axis->id);
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

    if (cmd == "STOP") {
        if (p1 < 0) {
            Serial.println("ERR,ALL,BAD_ARGS");
            return;
        }

        String target = line.substring(p1 + 1);
        target.trim();

        handleStop(target);
        return;
    }

    if (cmd == "JOG_START") {
        int p2 = line.indexOf(',', p1 + 1);
        if (p1 < 0 || p2 < 0) {
            Serial.println("ERR,ALL,BAD_ARGS");
            return;
        }

        String axisStr = line.substring(p1 + 1, p2);
        String sign = line.substring(p2 + 1);
        axisStr.trim();
        sign.trim();

        if (axisStr.length() != 1) {
            Serial.println("ERR,ALL,BAD_AXIS");
            return;
        }

        handleJogStart(axisStr[0], sign);
        return;
    }

    if (cmd == "JOG_STOP") {
        if (p1 < 0) {
            Serial.println("ERR,ALL,BAD_ARGS");
            return;
        }

        String target = line.substring(p1 + 1);
        target.trim();

        handleJogStop(target);
        return;
    }

    Serial.println("ERR,ALL,UNKNOWN_CMD");
}


void setup() {
    Serial.begin(115200);
    delay(500);

    pinMode(DEPTH_STEP_PIN, OUTPUT);
    pinMode(DEPTH_DIR_PIN, OUTPUT);
    pinMode(HEIGHT_STEP_PIN, OUTPUT);
    pinMode(HEIGHT_DIR_PIN, OUTPUT);

    digitalWrite(DEPTH_STEP_PIN, LOW);
    digitalWrite(DEPTH_DIR_PIN, LOW);
    digitalWrite(HEIGHT_STEP_PIN, LOW);
    digitalWrite(HEIGHT_DIR_PIN, LOW);
    // Depth axis init
    depth.id = 'D';
    depth.stepPin = DEPTH_STEP_PIN;
    depth.dirPin = DEPTH_DIR_PIN;
    depth.current = 0.0f;
    depth.commanded = 0.0f;
    depth.moving = false;
    depth.homed = false;
    depth.err = "";
    depth.motionDir = 0;
    depth.stepsRemaining = 0;
    depth.lastStepMicros = 0;
    depth.lastStateMicros = 0;

    // Height axis init
    height.id = 'H';
    height.stepPin = HEIGHT_STEP_PIN;
    height.dirPin = HEIGHT_DIR_PIN;
    height.current = 0.0f;
    height.commanded = 0.0f;
    height.moving = false;
    height.homed = false;
    height.err = "";
    height.motionDir = 0;
    height.stepsRemaining = 0;
    height.lastStepMicros = 0;
    height.lastStateMicros = 0;

    // Jogging axis init
    depth.jogging = false;
    height.jogging = false;
    
    Serial.println("OK,BOOT");
    emitAllStates();
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

    serviceMove(depth);
    serviceMove(height);
}