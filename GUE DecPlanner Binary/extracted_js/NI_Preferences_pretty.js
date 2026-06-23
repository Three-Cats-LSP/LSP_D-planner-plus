export default class NI {
  constructor() {
    this.METRIC = 0;
    this.IMPERIAL = 1;
    this.ALTITUDE_MAX = 3e3;
    this.METERS_TO_FEET = PI.conversions.feetPerMeter;
    this.BRIEF = 0;
    this.EXTENDED = 1;
    this.CONST = 1;
    this.stage_descr = [
      "descent",
      "bottom",
      "ascent",
      "waypoint",
      "ascent",
      "surface",
    ];
    this.ASCENT = 2;
    this.DESCENT = 0;
    this.DECO = 4;
    this.WAYPOINT = 3;
    this.SURFACE = 5;
    this.setDefaultPrefs();
  }
  getPrefs() {
    return this;
  }
  setDefaultPrefs() {
    this.units = this.METRIC;
    this.disableModUpdate = false;
    this.lastStopDepth = 3;
    this.stopDepthIncrement = 3;
    this.stopTimeIncrement = 1;
    this.extendedLimits = true;
    this.stopDepthMax = 10;
    this.stopDepthMin = 1;
    this.ascentRate = -9;
    this.ascentRateMin = -1;
    this.ascentRateMax = -10;
    this.descentRate = 20;
    this.descentRateMin = 5;
    this.descentRateMax = 50;
    this.gfHigh = 0.85;
    this.gfLow = 0.2;
    this.gfHigh_bailout = 0.9;
    this.gfLow_bailout = 0.9;
    this.bailout = true;
    this.gfMin = 0;
    this.gfMax = 0.95;
    this.diveRMV = 20;
    this.decoRMV = 15;
    this.pAmb = 10.1325;
    this.pConversionmsw = 10.1325;
    this.pConversion = this.pAmb;
    this.altitude = 0;
    this.pH2O = 0.627;
    this.pH2Omsw = 0.627;
    this.ocDeco = false;
    this.forceAllStops = true;
    this.runtimeFlag = true;
    this.gfMultilevelMode = true;
    this.prefGases = [];
    this.prefSegments = [];
    this.maxDepth = 330;
    this.maxSegmentTime = 1e3;
    this.maxSetpoint = 1.6;
    this.maxMOD = 1.607;
    this.maxPO2 = 1.6;
    this.agreedToTerms = false;
    this.modifiers = [0, 2, 4, 6, 8];
    this.factorComp = 1;
    this.factorDecomp = 1;
    this.modelClass = "ZHL16B";
    this.bottomppO2 = 1.2;
    this.decoppO2 = 1.2;
    this.oxygenppO2 = 1.5;
    this.configuration = "OC";
    this.helium_half_time_multiplier = 0;
    this.setExtendedLimits(8);
  }
  setLimits(t) {
    if (t) {
      this.gfMax = 1;
      this.maxSegmentTime = 1e4;
      this.maxSetpoint = 1.6;
      this.maxMOD = 1.607;
    } else {
      this.maxSegmentTime = 100;
      this.maxSetpoint = 1.6;
      this.maxMOD = 1.607;
      this.gfMax = 0.95;
    }
    if (this.units == this.METRIC) this.maxDepth = t ? 330 : 100;
    else this.maxDepth = t ? 1100 : 330;
  }
  setUnitsTo(t) {
    if (this.units == t) return;
    if (t != this.METRIC) {
      this.units = this.IMPERIAL;
      this.lastStopDepth = 10;
      this.stopDepthIncrement = 10;
      this.stopDepthMax = 33;
      this.stopDepthMin = 3;
      this.ascentRate = -30;
      this.ascentRateMin = -3;
      this.ascentRateMax = -33;
      this.descentRate = 60;
      this.descentRateMin = 16;
      this.descentRateMax = 160;
      this.pAmb = 33;
      this.pH2O = 2.0461;
      this.maxDepth = 1e3;
    } else {
      this.units = this.METRIC;
      this.lastStopDepth = 3;
      this.stopDepthIncrement = 3;
      this.stopDepthMax = 10;
      this.stopDepthMin = 1;
      this.ascentRate = -9;
      this.ascentRateMin = -1;
      this.ascentRateMax = -10;
      this.descentRate = 20;
      this.descentRateMin = 5;
      this.descentRateMax = 50;
      this.pAmb = 10.1325;
      this.pH2O = 0.627;
      this.maxDepth = 330;
    }
    this.pConversion = this.pAmb;
  }
  setAltitude(t) {
    if (this.units == this.METRIC) {
      if (t < 0 || t > this.ALTITUDE_MAX) t = 0;
      this.pAmb = this.altitudeToPressure(t);
      this.altitude = t;
    } else {
      if (t < 0 || t > this.ALTITUDE_MAX * this.METERS_TO_FEET) t = 0;
      this.pAmb =
        this.altitudeToPressure(t / this.METERS_TO_FEET) * this.METERS_TO_FEET;
      this.altitude = t;
    }
  }
  altitudeToPressure(t) {
    if (t == 0) return this.pAmb;
    else if (t > 0) return Math.pow((44330.8 - t) / 4946.54, 5.25588) / 10131;
    else return 0;
  }
  isDisableModUpdate() {
    return this.disableModUpdate;
  }
  getLastStopDepth() {
    return this.lastStopDepth;
  }
  getStopDepthIncrement() {
    return this.stopDepthIncrement;
  }
  getStopTimeIncrement() {
    return this.stopTimeIncrement;
  }
  getStopDepthMax() {
    return this.stopDepthMax;
  }
  getStopDepthMin() {
    return this.stopDepthMin;
  }
  getAscentRate() {
    return this.ascentRate;
  }
  getAscentRateMax() {
    return this.ascentRateMax;
  }
  getAscentRateMin() {
    return this.ascentRateMin;
  }
  getDescentRate() {
    return this.descentRate;
  }
  getDescentRateMax() {
    return this.descentRateMax;
  }
  getDescentRateMin() {
    return this.descentRateMin;
  }
  getExtendedLimits() {
    return this.extendedLimits;
  }
  getGfHigh() {
    if (this.getBailout() && this.configuration != "OC") {
      return this.gfHigh_bailout;
    } else {
      return this.gfHigh;
    }
  }
  getGfLow() {
    if (this.getBailout() && this.configuration != "OC") {
      return this.gfLow_bailout;
    } else {
      return this.gfLow;
    }
  }
  getGfMax() {
    return this.gfMax;
  }
  getGfMin() {
    return this.gfMin;
  }
  getDecoRMV() {
    return this.decoRMV;
  }
  getDiveRMV() {
    return this.diveRMV;
  }
  getOcDeco() {
    return this.ocDeco;
  }
  getForceAllStops() {
    return this.forceAllStops;
  }
  getRuntimeFlag() {
    return this.runtimeFlag;
  }
  getGfMultilevelMode() {
    return this.gfMultilevelMode;
  }
  getPrefGases() {
    return this.prefGases;
  }
  getPrefSegments() {
    return this.prefSegments;
  }
  getLastModelFile() {
    return this.lastModelFile;
  }
  getPAmb() {
    return this.pAmb;
  }
  getPConversion() {
    return this.pConversion;
  }
  getPConversioninMsw() {
    return this.pConversionmsw;
  }
  getPH2O() {
    return this.pH2O;
  }
  getPH2Omsw() {
    return this.pH2Omsw;
  }
  getAltitude() {
    return this.altitude;
  }
  getAltitudeInMsw() {
    return this.units ? PI.feetToMeters(this.altitude, 0) : this.altitude;
  }
  getAgreedToTerms() {
    return this.agreedToTerms;
  }
  getMaxDepth() {
    return this.maxDepth;
  }
  getMaxSegmentTime() {
    return this.maxSegmentTime;
  }
  getMaxSetpoint() {
    return this.maxSetpoint;
  }
  getMaxMOD() {
    return this.maxMOD;
  }
  getMaxPO2() {
    return this.maxPO2;
  }
  getModifiers() {
    return this.modifiers;
  }
  getFactorComp() {
    return this.factorComp;
  }
  getFactorDecomp() {
    return this.factorDecomp;
  }
  getBailout() {
    return this.bailout;
  }
  setDisableModUpdate(t) {
    this.disableModUpdate = t;
  }
  setLastStopDepth(t) {
    this.lastStopDepth = t;
  }
  setStopDepthIncrement(t) {
    this.stopDepthIncrement = t;
  }
  setStopTimeIncrement(t) {
    this.stopTimeIncrement = t;
  }
  setAscentRate(t) {
    this.ascentRate = -t;
  }
  setDescentRate(t) {
    this.descentRate = t;
  }
  setGfHigh(t) {
    this.gfHigh = t;
  }
  setGfLow(t) {
    this.gfLow = t;
  }
  setGfHigh_bailout(t) {
    this.gfHigh_bailout = t;
  }
  setGfLow_bailout(t) {
    this.gfLow_bailout = t;
  }
  setDecoRMV(t) {
    this.decoRMV = t;
  }
  setDiveRMV(t) {
    this.diveRMV = t;
  }
  setOcDeco(t) {
    this.ocDeco = t;
  }
  setForceAllStops(t) {
    this.forceAllStops = t;
  }
  setRuntimeFlag(t) {
    this.runtimeFlag = t;
  }
  setGfMultilevelMode(t) {
    this.gfMultilevelMode = t;
  }
  setPrefGases(t) {
    this.prefGases = t;
  }
  setPrefSegments(t) {
    this.prefSegments = t;
  }
  setLastModelFile(t) {
    this.lastModelFile = t;
  }
  setPAmb(t) {
    this.pAmb = t;
  }
  setPH2O(t) {
    this.pH2O = t;
  }
  setAgreedToTerms(t) {
    this.agreedToTerms = t;
  }
  setModifiers(t) {
    this.modifiers = t;
  }
  setFactorComp(t) {
    this.factorComp = t;
  }
  setFactorDecomp(t) {
    this.factorDecomp = t;
  }
  setConfiguration(t) {
    this.configuration = t;
  }
  setBailout(t) {
    this.bailout = t;
  }
  setHelium_half_time_multiplier(t) {
    this.helium_half_time_multiplier = parseFloat(t);
  }
  setExtendedLimits(t) {
    this.extendedLimits = t;
    this.setLimits(this.extendedLimits);
  }
  getUnits() {
    return this.units;
  }
  setUnits(t) {
    this.units = t;
  }
}
