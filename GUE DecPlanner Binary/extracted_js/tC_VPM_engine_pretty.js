export default class tC {
  constructor() {
    this.critical_radius_n2_microns_basic = 0.55;
    this.critical_radius_he_microns_basic = 0.45;
    this.crit_volume_parameter_lambda = 6500;
    this.gradient_onset_of_imperm_atm = 8.2;
    this.surface_tension_gamma = 0.0179;
    this.skin_compression_gammac = 0.257;
    this.regeneration_time_constant = 20160;
    this.pressure_other_gases_mmhg = 102;
    this.MAX_DECO_MIXES = 5;
    this.MAX_BOTTOM_MIXES = 5;
    this.MAX_PROFILE_POINTS = 10;
    this.MAX_OUTPUT_POINTS = 70;
    this.MAX_DIVES = 5;
    this.tissues = [];
    this.pref = new NI();
    this.diveBuhlmann = new QI();
    this.calc_deco_ceiling = function () {
      let t;
      let e, i;
      let n;
      let s = new Array();
      for (t = 1; t <= 16; ++t) {
        e = this.helium_pressure[t - 1] + this.nitrogen_pressure[t - 1];
        if (e > 0) {
          i =
            (this.deco_gradient_he[t - 1] * this.helium_pressure[t - 1] +
              this.deco_gradient_n2[t - 1] * this.nitrogen_pressure[t - 1]) /
            (this.helium_pressure[t - 1] + this.nitrogen_pressure[t - 1]);
          n = e + this.constant_pressure_other_gases - i;
        } else {
          i = Math.min(
            this.deco_gradient_he[t - 1],
            this.deco_gradient_n2[t - 1],
          );
          n = this.constant_pressure_other_gases - i;
        }
        if (n < 0) {
          n = 0;
        }
        s[t - 1] = n - this.barometric_pressure;
      }
      this.deco_ceiling_depth = s[0];
      for (t = 2; t <= 16; ++t) {
        this.deco_ceiling_depth = Math.max(this.deco_ceiling_depth, s[t - 1]);
      }
      return 0;
    };
    this.vpm_repetitive_algorithm = function (t) {
      let e;
      let i;
      let n, s, r, o;
      for (i = 1; i <= 16; ++i) {
        e = (this.max_actual_gradient[i - 1] / this.units_factor) * 101325;
        r =
          (this.adjusted_crushing_pressure_he[i - 1] / this.units_factor) *
          101325;
        n =
          (this.adjusted_crushing_pressure_n2[i - 1] / this.units_factor) *
          101325;
        if (
          this.max_actual_gradient[i - 1] >
          this.initial_allowable_gradient_n2[i - 1]
        ) {
          s =
            (this.surface_tension_gamma *
              2 *
              (this.skin_compression_gammac - this.surface_tension_gamma)) /
            (e * this.skin_compression_gammac - this.surface_tension_gamma * n);
          this.adjusted_critical_radius_n2[i - 1] =
            this.initial_critical_radius_n2[i - 1] +
            (this.initial_critical_radius_n2[i - 1] - s) *
              Math.exp(-t / this.regeneration_time_constant);
        } else {
          this.adjusted_critical_radius_n2[i - 1] =
            this.initial_critical_radius_n2[i - 1];
        }
        if (
          this.max_actual_gradient[i - 1] >
          this.initial_allowable_gradient_he[i - 1]
        ) {
          o =
            (this.surface_tension_gamma *
              2 *
              (this.skin_compression_gammac - this.surface_tension_gamma)) /
            (e * this.skin_compression_gammac - this.surface_tension_gamma * r);
          this.adjusted_critical_radius_he[i - 1] =
            this.initial_critical_radius_he[i - 1] +
            (this.initial_critical_radius_he[i - 1] - o) *
              Math.exp(-t / this.regeneration_time_constant);
        } else {
          this.adjusted_critical_radius_he[i - 1] =
            this.initial_critical_radius_he[i - 1];
        }
      }
      return 0;
    };
    this.configuration = "OC";
    this.conservatism = 2;
    this.deco_gas_switch_time = 1;
    this.lastStop6m20ft = false;
    this.altitude_dive_algorithm = "off";
    this.minimum_deco_stop_time = 1;
    this.critical_volume_algorithm = "on";
    this.diver_acclimatized_at_altitude = "no";
    this.starting_acclimatized_altitude = 0;
    this.ascent_to_altitude_hours = 2;
    this.hours_at_altitude_before_dive = 3;
    this.helium_half_time_multiplier = 0;
    this.descentppO2 = 0.7;
    this.VPM_gf_high = 90;
    this.VPM_GFS = false;
    let t = "Metric";
    this.setUnits(t);
    this.dive_no = 0;
    this.bottomMixSetPoint = new Array();
    this.decoMixSetPoint = new Array();
    this.decoMixUseDiluentGas = new Array();
    this.decoMixfO2 = new Array();
    this.decoMixfHe = new Array();
    this.decoMOD = new Array();
    this.bottomMixfO2 = new Array();
    this.bottomMixfHe = new Array();
    this.profileDepth = new Array();
    this.profileTime = new Array();
    this.profileMix = new Array();
    this.profileDecAccSpeed = new Array();
    this.surfaceIntervals = new Array();
    this.outputProfileDepth = new Array();
    this.outputProfileTime = new Array();
    this.outputProfileSegmentTime = new Array();
    this.outputProfileSegmentType = new Array();
    this.outputProfileMixO2 = new Array();
    this.outputProfileMixHe = new Array();
    this.outputProfileGas = new Array();
    this.outputProfileCounter = 0;
    this.decoProfileCalculated = false;
    this.outputStartOfDecoDepth = new Array();
    this.firstDecoProfilePoint = null;
    this.firstDecoPoint = new Array();
    this.deco_ceiling_depth = null;
    this.ascent_ceiling_depth = null;
    this.deco_stop_depth = null;
    this.next_deco_stop_depth = null;
    this.err = null;
    this.fO2 = null;
    this.fHe = null;
    this.fN2 = null;
    this.dc = null;
    this.rc = null;
    this.ssc = null;
    this.mc = null;
    this.water_vapor_pressure = null;
    this.run_time = null;
    this.segment_number = null;
    this.segment_time = null;
    this.ending_ambient_pressure = null;
    this.mix_number = null;
    this.barometric_pressure = null;
    this.units_equal_fsw = null;
    this.units_equal_msw = null;
    this.units_factor = null;
    this.helium_time_constant = new Array();
    this.nitrogen_time_constant = new Array();
    this.helium_pressure = new Array();
    this.nitrogen_pressure = new Array();
    this.fraction_helium = new Array();
    this.fraction_nitrogen = new Array();
    this.fraction_pO2SetPoint = new Array();
    this.fraction_useDiluentGas = new Array();
    this.initial_critical_radius_he = new Array();
    this.initial_critical_radius_n2 = new Array();
    this.adjusted_critical_radius_he = new Array();
    this.adjusted_critical_radius_n2 = new Array();
    this.max_crushing_pressure_he = new Array();
    this.max_crushing_pressure_n2 = new Array();
    this.surface_phase_volume_time = new Array();
    this.max_actual_gradient = new Array();
    this.amb_pressure_onset_of_imperm = new Array();
    this.gas_tension_onset_of_imperm = new Array();
    this.initial_helium_pressure = new Array();
    this.initial_nitrogen_pressure = new Array();
    this.regenerated_radius_he = new Array();
    this.regenerated_radius_n2 = new Array();
    this.adjusted_crushing_pressure_he = new Array();
    this.adjusted_crushing_pressure_n2 = new Array();
    this.allowable_gradient_he = new Array();
    this.allowable_gradient_n2 = new Array();
    this.deco_gradient_he = new Array();
    this.deco_gradient_n2 = new Array();
    this.initial_allowable_gradient_he = new Array();
    this.initial_allowable_gradient_n2 = new Array();
    this.constant_pressure_other_gases = null;
  }
  setUnits(t) {
    if (t === "Imperial") {
      this.units = "ft";
      this.altitude_of_dive = 3300;
      this.decoStepSize = 10;
      this.finalAscentSpeed = -30;
    } else {
      this.units = "mt";
      this.altitude_of_dive = 1e3;
      this.decoStepSize = 3;
      this.finalAscentSpeed = -9;
    }
    this.pref.setUnitsTo(t == "Metric" ? 0 : 1);
  }
  newMission() {
    let t, e;
    for (t = 0; t <= this.MAX_DECO_MIXES; t++) {
      if (!Array.isArray(this.decoMixfO2[t])) this.decoMixfO2[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.decoMixfO2[t][e] = -1;
      if (!Array.isArray(this.decoMixfHe[t])) this.decoMixfHe[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.decoMixfHe[t][e] = -1;
      if (!Array.isArray(this.decoMOD[t])) this.decoMOD[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.decoMOD[t][e] = -1;
      if (!Array.isArray(this.decoMixSetPoint[t]))
        this.decoMixSetPoint[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.decoMixSetPoint[t][e] = -1;
      if (!Array.isArray(this.decoMixUseDiluentGas[t]))
        this.decoMixUseDiluentGas[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++)
        this.decoMixUseDiluentGas[t][e] = -1;
    }
    for (t = 0; t <= this.MAX_BOTTOM_MIXES; t++) {
      if (!Array.isArray(this.bottomMixfO2[t]))
        this.bottomMixfO2[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.bottomMixfO2[t][e] = -1;
      if (!Array.isArray(this.bottomMixfHe[t]))
        this.bottomMixfHe[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.bottomMixfHe[t][e] = -1;
      if (!Array.isArray(this.bottomMixSetPoint[t]))
        this.bottomMixSetPoint[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.bottomMixSetPoint[t][e] = -1;
    }
    for (t = 0; t <= this.MAX_PROFILE_POINTS; t++) {
      if (!Array.isArray(this.profileDepth[t]))
        this.profileDepth[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.profileDepth[t][e] = -1;
      if (!Array.isArray(this.profileTime[t]))
        this.profileTime[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.profileTime[t][e] = -1;
      if (!Array.isArray(this.profileMix[t])) this.profileMix[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.profileMix[t][e] = -1;
      if (!Array.isArray(this.profileDecAccSpeed[t]))
        this.profileDecAccSpeed[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.profileDecAccSpeed[t][e] = -1;
    }
    for (t = 0; t <= this.MAX_OUTPUT_POINTS; t++) {
      if (!Array.isArray(this.outputProfileDepth[t]))
        this.outputProfileDepth[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.outputProfileDepth[t][e] = -1;
      if (!Array.isArray(this.outputProfileTime[t]))
        this.outputProfileTime[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.outputProfileTime[t][e] = -1;
      if (!Array.isArray(this.outputProfileSegmentTime[t]))
        this.outputProfileSegmentTime[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++)
        this.outputProfileSegmentTime[t][e] = -1;
      if (!Array.isArray(this.outputProfileSegmentType[t]))
        this.outputProfileSegmentType[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++)
        this.outputProfileSegmentType[t][e] = -1;
      if (!Array.isArray(this.outputProfileMixO2[t]))
        this.outputProfileMixO2[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.outputProfileMixO2[t][e] = -1;
      if (!Array.isArray(this.outputProfileMixHe[t]))
        this.outputProfileMixHe[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.outputProfileMixHe[t][e] = -1;
      if (!Array.isArray(this.outputProfileGas[t]))
        this.outputProfileGas[t] = new Array();
      for (e = 0; e <= this.MAX_DIVES; e++) this.outputProfileGas[t][e] = -1;
    }
    this.outputProfileGasRuntime = new Array();
    for (e = 0; e <= this.MAX_DIVES; e++) this.outputProfileGasRuntime[e] = {};
    this.minimum_profile_depth = new Array();
    for (e = 0; e <= this.MAX_DIVES; e++) this.minimum_profile_depth[e] = 1e7;
    this.dive_no = 0;
    this.decoProfileCalculated = false;
  }
  addSurfaceInterval(t) {
    if (this.dive_no < this.MAX_DIVES - 1) {
      this.dive_no++;
      this.surfaceIntervals[this.dive_no] = t;
      return this.dive_no;
    }
    return -1;
  }
  addBottomMix(t, e, i) {
    let n;
    if (t + e > 1 || t < 0.01 || e < 0) return -1;
    for (n = 0; n < this.MAX_BOTTOM_MIXES; n++) {
      if (this.bottomMixfO2[n][this.dive_no] == -1) {
        this.bottomMixfO2[n][this.dive_no] = t;
        this.bottomMixfHe[n][this.dive_no] = e;
        this.bottomMixSetPoint[n][this.dive_no] = i;
        return n;
      }
    }
    return -1;
  }
  addDecoMix(t, e, i, n, s) {
    let r;
    if (t + e > 1 || t < 0.01 || e < 0) return -1;
    for (r = 0; r < this.MAX_DECO_MIXES; r++) {
      if (r > 0 && i >= this.decoMOD[r - 1][this.dive_no]) return -1;
      if (this.decoMixfO2[r][this.dive_no] == -1) {
        this.decoMixfO2[r][this.dive_no] = t;
        this.decoMixfHe[r][this.dive_no] = e;
        this.decoMOD[r][this.dive_no] = i;
        this.decoMixSetPoint[r][this.dive_no] = n;
        this.decoMixUseDiluentGas[r][this.dive_no] = s;
        return r;
      }
    }
    return -1;
  }
  addProfilePoint(t, e, i, n) {
    let s;
    if (t < 0 || n < 0 || n >= this.MAX_DECO_MIXES) return -1;
    for (s = 0; s < this.MAX_PROFILE_POINTS; s++) {
      if (this.profileDepth[s][this.dive_no] == -1) {
        if (s != 0 && t < this.profileDepth[s - 1][this.dive_no] && i >= 0)
          return -1;
        if (s != 0 && t > this.profileDepth[s - 1][this.dive_no] && i <= 0)
          return -1;
        if (s == 0 && i <= 0) return -1;
        this.profileDepth[s][this.dive_no] = t;
        this.profileTime[s][this.dive_no] = e;
        this.profileMix[s][this.dive_no] = n;
        this.profileDecAccSpeed[s][this.dive_no] = i;
        this.minimum_profile_depth[this.dive_no] =
          this.minimum_profile_depth[this.dive_no] < t
            ? this.minimum_profile_depth[this.dive_no]
            : t;
        return s;
      }
    }
    return 1;
  }
  getProfilePoint(t, e, i) {
    if (
      this.decoProfileCalculated == false ||
      t >= this.MAX_OUTPUT_POINTS ||
      i >= this.MAX_DIVES
    )
      return -1;
    if (this.outputProfileDepth[t][i] == -1) return -1;
    switch (e) {
      case 1:
        return this.outputProfileDepth[t][i];
      case 2:
        return this.outputProfileTime[t][i];
      case 3:
        return this.outputProfileSegmentTime[t][i];
      case 4:
        return this.outputProfileMixO2[t][i];
      case 5:
        return this.outputProfileMixHe[t][i];
      case 6:
        return this.outputProfileSegmentType[t][i];
    }
    return -1;
  }
  addInspiredGasRuntime(t, e, i) {
    if (!this.outputProfileGasRuntime[this.current_dive_number][t + "/" + e])
      this.outputProfileGasRuntime[this.current_dive_number][t + "/" + e] = 0;
    this.outputProfileGasRuntime[this.current_dive_number][t + "/" + e] += i;
  }
  getProfileGasIndex(t, e) {
    if (
      this.decoProfileCalculated == false ||
      t >= this.MAX_OUTPUT_POINTS ||
      e >= this.MAX_DIVES
    )
      return -1;
    if (this.outputProfileDepth[t][e] == -1) return -1;
    return this.outputProfileGas[t][e];
  }
  runVPM(t, e) {
    this.newMission();
    this.run_bailout = e;
    let i = t;
    i.diveMixO2 = new Array();
    i.diveMixHe = new Array();
    i.diveMixSetPoint = new Array();
    i.diveMixUseDiluentGas = new Array();
    i.diveGas = new Array();
    let n = 0;
    i.noBottomMix = new Array();
    this.decoStepSize = t.parameters.decoStepSize;
    this.descentppO2 = t.parameters.descentppO2;
    this.conservatism = e
      ? t.parameters.conservatism_bailout
      : t.parameters.conservatism;
    this.configuration = t.parameters.configuration;
    this.deco_gas_switch_time = t.parameters.time_at_gas_switch_for_min_gas;
    this.lastStop6m20ft = t.parameters.lastStop6m20ft;
    this.critical_volume_algorithm = t.parameters.critical_volume_algorithm
      ? "on"
      : "off";
    this.altitude_dive_algorithm = t.parameters.altitude_dive_algorithm;
    this.altitude_of_dive = t.parameters.altitude_of_dive;
    this.ascent_to_altitude_hours = t.parameters.ascent_to_altitude_hours;
    this.hours_at_altitude_before_dive =
      t.parameters.hours_at_altitude_before_dive;
    this.metabolic_o2_consumption = t.parameters.metabolic_o2_consumption;
    this.rmv = t.parameters.rmvBottom;
    this.helium_half_time_multiplier = parseFloat(
      t.parameters.helium_half_time_multiplier,
    );
    this.VPM_GFS = t.parameters.VPM_GFS;
    this.VPM_gf_high = t.parameters.VPM_gf_high;
    let s;
    let r, o;
    for (let e = 0; e < this.MAX_BOTTOM_MIXES + t.parameters.MAX_DECOMIX; e++) {
      for (let t = 0; t < this.MAX_DIVES; t++) {
        if (!Array.isArray(i.diveMixO2[e])) i.diveMixO2[e] = new Array();
        i.diveMixO2[e][t] = -1;
        if (!Array.isArray(i.diveMixHe[e])) i.diveMixHe[e] = new Array();
        i.diveMixHe[e][t] = -1;
        if (!Array.isArray(i.diveMixSetPoint[e]))
          i.diveMixSetPoint[e] = new Array();
        i.diveMixSetPoint[e][t] = -1;
        if (!Array.isArray(i.diveMixUseDiluentGas[e]))
          i.diveMixUseDiluentGas[e] = new Array();
        i.diveMixUseDiluentGas[e][t] = -1;
      }
      i.diveGas[e] = 0;
    }
    for (n = 0; n < this.MAX_DIVES; n++) {
      i.noBottomMix[n] = 0;
      for (let e = 0; e < t.parameters.MAX_DIVEPONTS; e++) {
        if (t.profilePointDepth[e][n] < 0) {
          if (e == 0) {
            let e = this.addBottomMix(0.21, 0, 0);
            this.addProfilePoint(0, 0, parseFloat(t.parameters.descentRate), e);
          }
          break;
        }
        for (let o = 0; true; o++) {
          if (o == this.MAX_BOTTOM_MIXES) {
            s += "Max. number of bottom mixes exceded - " + o;
            console.log("1", s);
            return;
          }
          if (i.diveMixO2[o][n] == -1) {
            r = this.addBottomMix(
              t.profilePointMixO2[e][n] / 100,
              t.profilePointMixHe[e][n] / 100,
              t.profilePointMixSetPoint[e][n],
            );
            if (r < 0) {
              s += "Internal ERROR 1: mix=" + r + "divepoint=" + e + "\n";
              console.log("2", s);
              return;
            }
            i.diveMixO2[r][n] = t.profilePointMixO2[e][n];
            i.diveMixHe[r][n] = t.profilePointMixHe[e][n];
            i.diveMixSetPoint[r][n] = t.profilePointMixSetPoint[e][n];
            i.diveMixUseDiluentGas[r][n] = true;
            break;
          }
          if (
            t.profilePointMixO2[e][n] == i.diveMixO2[o][n] &&
            t.profilePointMixHe[e][n] == i.diveMixHe[o][n]
          ) {
            r = o;
            break;
          }
        }
        if (r > i.noBottomMix[n]) i.noBottomMix[n] = r;
        if (e == 0) o = parseFloat(t.parameters.descentRate);
        else if (t.profilePointDepth[e][n] > t.profilePointDepth[e - 1][n])
          o = parseFloat(t.parameters.descentRate);
        else o = -parseFloat(t.parameters.ascentRate);
        if (
          this.addProfilePoint(
            t.profilePointDepth[e][n],
            t.profilePointRT[e][n],
            o,
            r,
          ) < 0
        ) {
          s += "Internal ERROR 2\n";
          console.log("3", s);
          return;
        }
      }
      for (let e = 0; e < t.parameters.MAX_DECOMIX; e++) {
        if (t.decomixfromdepth[e][n] < 0) break;
        let r = this.addDecoMix(
          t.decomixO2[e][n] / 100,
          t.decomixHe[e][n] / 100,
          t.decomixfromdepth[e][n],
          t.decomixSetPoint[e][n],
          t.decomixUseDiluentGas[e][n],
        );
        if (r < 0) {
          s +=
            "Internal ERROR 0: " +
            t.decomixO2[e][n] / 100 +
            "-" +
            t.decomixHe[e][n] / 100;
          console.log("4", s);
          return;
        }
        i.diveMixO2[i.noBottomMix[n] + 1 + e][n] = t.decomixO2[e][n];
        i.diveMixHe[i.noBottomMix[n] + 1 + e][n] = t.decomixHe[e][n];
        i.diveMixSetPoint[i.noBottomMix[n] + 1 + e][n] =
          t.decomixSetPoint[e][n];
        i.diveMixUseDiluentGas[i.noBottomMix[n] + 1 + e][n] =
          t.decomixUseDiluentGas[e][n];
      }
      if (n < this.MAX_DIVES - 1)
        if (this.addSurfaceInterval(t.surfaceIntervals[n + 1]) < 0) {
          s += "Internal ERROR 0.1: " + n;
          console.log("5", s);
        }
    }
    this.finalAscentSpeed = -parseFloat(t.parameters.ascentRate);
    let a = this.calculate();
    if (a < -1) {
      console.log(
        "Dive #" +
          (-a / 100 + 1) +
          " Dive Point " +
          ((-a % 100) + 1) +
          " to deep\n",
      );
      return false;
    } else if (a < 0) {
      console.log("VPM Internal ERROR 3");
      return false;
    }
    return true;
  }
  calculate() {
    let t = [
      [1.88, 5],
      [3.02, 8],
      [4.72, 12.5],
      [6.99, 18.5],
      [10.21, 27],
      [14.48, 38.3],
      [20.53, 54.3],
      [29.11, 77],
      [41.2, 109],
      [55.19, 146],
      [70.69, 187],
      [90.34, 239],
      [115.29, 305],
      [147.42, 390],
      [188.24, 498],
      [240.03, 635],
    ];
    let e = [];
    let i = [];
    for (let n = 0; n < 16; n++) {
      if (this.helium_half_time_multiplier >= 0) {
        e[n] = ((t[n][1] - t[n][0]) / 10.1) * this.helium_half_time_multiplier;
        i[n] = 0;
      } else {
        e[n] = 0;
        i[n] = ((t[n][1] - t[n][0]) / 10.1) * this.helium_half_time_multiplier;
      }
    }
    for (let t = 0; t < 16; t++) {
      this.tissues[t] = new qI(this.pref, this.diveBuhlmann.getAmbientPress());
      this.tissues[t].setPpHe(0);
      this.tissues[t].setPpN2(
        0.79 * (this.diveBuhlmann.getAmbientPress() - this.pref.getPH2O()),
      );
    }
    let n = new Array(
      1.88 + e[0],
      3.02 + e[1],
      4.72 + e[2],
      6.99 + e[3],
      10.21 + e[4],
      14.48 + e[5],
      20.53 + e[6],
      29.11 + e[7],
      41.2 + e[8],
      55.19 + e[9],
      70.69 + e[10],
      90.34 + e[11],
      115.29 + e[12],
      147.42 + e[13],
      188.24 + e[14],
      240.03 + e[15],
    );
    let s = new Array(
      5 + i[0],
      8 + i[1],
      12.5 + i[2],
      18.5 + i[3],
      27 + i[4],
      38.3 + i[5],
      54.3 + i[6],
      77 + i[7],
      109 + i[8],
      146 + i[9],
      187 + i[10],
      239 + i[11],
      305 + i[12],
      390 + i[13],
      498 + i[14],
      635 + i[15],
    );
    let r, o;
    ((this.critical_radius_n2_microns =
      this.critical_radius_n2_microns_basic + this.conservatism / 20),
      (this.critical_radius_he_microns =
        this.critical_radius_he_microns_basic + this.conservatism / 20));
    let a = new Array(),
      h,
      c,
      u = new Array(),
      l = new Array(),
      f,
      d,
      p,
      m,
      g = new Array(),
      v,
      w = new Array(),
      _,
      b,
      y,
      x,
      M,
      T,
      E,
      A,
      S,
      k,
      I = new Array(),
      C,
      O = new Array();
    let D,
      R,
      P,
      N,
      F = new Array(),
      j = new Array(),
      L = new Array(),
      z,
      $,
      U,
      B,
      G = new Array(),
      V = 0,
      H,
      W,
      q = 0;
    this.current_dive_number = 0;
    let Y = true;
    if (this.units == "ft" || this.units == "FT") {
      this.units_equal_fsw = true;
      this.units_equal_msw = false;
    } else if (this.units == "mt" || this.units == "MT") {
      this.units_equal_fsw = false;
      this.units_equal_msw = true;
    } else {
      return -1;
    }
    if (
      this.altitude_dive_algorithm == "ON" ||
      this.altitude_dive_algorithm == "on"
    ) {
      f = false;
    } else {
      f = true;
    }
    if (
      this.critical_radius_n2_microns < 0.2 ||
      this.critical_radius_n2_microns > 1.35
    ) {
      console.log(
        "critical_radius_n2_microns out of range",
        this.critical_radius_n2_microns,
      );
      return -1;
    }
    if (
      this.critical_radius_he_microns < 0.2 ||
      this.critical_radius_he_microns > 1.35
    ) {
      console.log(
        "critical_radius_he_microns out of range",
        this.critical_radius_he_microns,
      );
      return -1;
    }
    if (
      this.critical_volume_algorithm == "ON" ||
      this.critical_volume_algorithm == "on"
    ) {
      D = false;
    } else {
      D = true;
    }
    if (this.units_equal_fsw) {
      this.units_factor = 33;
      this.water_vapor_pressure = 1.607;
    } else {
      this.units_factor = 10.1325;
      this.water_vapor_pressure = 0.493;
    }
    this.constant_pressure_other_gases =
      (this.pressure_other_gases_mmhg / 760) * this.units_factor;
    this.run_time = 0;
    this.segment_number = 0;
    for (_ = 1; _ <= 16; ++_) {
      this.helium_time_constant[_ - 1] = Math.log(2) / n[_ - 1];
      this.nitrogen_time_constant[_ - 1] = Math.log(2) / s[_ - 1];
      this.max_crushing_pressure_he[_ - 1] = 0;
      this.max_crushing_pressure_n2[_ - 1] = 0;
      this.max_actual_gradient[_ - 1] = 0;
      this.surface_phase_volume_time[_ - 1] = 0;
      this.amb_pressure_onset_of_imperm[_ - 1] = 0;
      this.gas_tension_onset_of_imperm[_ - 1] = 0;
      this.initial_critical_radius_n2[_ - 1] =
        this.critical_radius_n2_microns * 1e-6;
      this.initial_critical_radius_he[_ - 1] =
        this.critical_radius_he_microns * 1e-6;
    }
    if (f) {
      v = 0;
      this.calc_barometric_pressure(v);
      for (_ = 1; _ <= 16; ++_) {
        this.adjusted_critical_radius_n2[_ - 1] =
          this.initial_critical_radius_n2[_ - 1];
        this.adjusted_critical_radius_he[_ - 1] =
          this.initial_critical_radius_he[_ - 1];
        this.helium_pressure[_ - 1] = 0;
        this.nitrogen_pressure[_ - 1] =
          (this.barometric_pressure - this.water_vapor_pressure) * 0.79;
      }
    } else {
      this.vpm_altitude_dive_algorithm();
    }
    while (true) {
      this.outputProfileCounter = 0;
      h = 0;
      for (_ = 1; _ <= this.MAX_BOTTOM_MIXES; ++_) {
        if (this.bottomMixfO2[_ - 1][this.current_dive_number] < 0) break;
        a[_ - 1] = this.bottomMixfO2[_ - 1][this.current_dive_number];
        this.fraction_helium[_ - 1] =
          this.bottomMixfHe[_ - 1][this.current_dive_number];
        this.fraction_nitrogen[_ - 1] =
          1 -
          this.bottomMixfO2[_ - 1][this.current_dive_number] -
          this.bottomMixfHe[_ - 1][this.current_dive_number];
        this.fraction_pO2SetPoint[_ - 1] =
          this.bottomMixSetPoint[_ - 1][this.current_dive_number];
        this.fraction_useDiluentGas[_ - 1] = true;
      }
      W = _ - 1;
      for (b = 1; b <= this.MAX_DECO_MIXES; ++b) {
        if (this.decoMixfO2[b - 1][this.current_dive_number] < 0) break;
        a[_ + b - 2] = this.decoMixfO2[b - 1][this.current_dive_number];
        this.fraction_helium[_ + b - 2] =
          this.decoMixfHe[b - 1][this.current_dive_number];
        this.fraction_nitrogen[_ + b - 2] =
          1 -
          this.decoMixfO2[b - 1][this.current_dive_number] -
          this.decoMixfHe[b - 1][this.current_dive_number];
        if (this.run_bailout) {
          this.fraction_pO2SetPoint[_ + b - 2] = 0;
          this.fraction_useDiluentGas[_ + b - 2] = true;
        } else {
          this.fraction_pO2SetPoint[_ + b - 2] =
            this.decoMixSetPoint[b - 1][this.current_dive_number];
          this.fraction_useDiluentGas[_ + b - 2] =
            this.decoMixUseDiluentGas[b - 1][this.current_dive_number];
        }
      }
      H = b - 1;
      _ = 0;
      m = -1;
      while (true) {
        if (this.profileDepth[_][this.current_dive_number] < 0) break;
        if (this.profileDepth[_][this.current_dive_number] < m) break;
        if (_ == 0) {
          this.mix_number = this.profileMix[_][this.current_dive_number] + 1;
          P = 0;
        } else {
          this.mix_number =
            this.profileMix[_ - 1][this.current_dive_number] + 1;
          P = this.profileDepth[_ - 1][this.current_dive_number];
        }
        d = this.profileDepth[_][this.current_dive_number];
        c = this.profileDecAccSpeed[_][this.current_dive_number];
        this.gas_loadings_ascent_descent(P, d, c);
        if (d > P) {
          this.calc_crushing_pressure(P, d, c);
        }
        if (_ >= 0) {
          this.outputProfileDepth[this.outputProfileCounter][
            this.current_dive_number
          ] = d;
          this.outputProfileTime[this.outputProfileCounter][
            this.current_dive_number
          ] = this.run_time;
          this.outputProfileSegmentTime[this.outputProfileCounter][
            this.current_dive_number
          ] = this.segment_time;
          if (P < d) {
            this.outputProfileSegmentType[this.outputProfileCounter][
              this.current_dive_number
            ] = "descent";
          } else {
            this.outputProfileSegmentType[this.outputProfileCounter][
              this.current_dive_number
            ] = "bottom_ascent";
          }
          let t = false;
          if (_ == 0) {
            t = this.run_bailout;
          }
          if (t) this.run_bailout = false;
          let e = this.calc_inspired_gas(
            d - (d - P) / 2 + this.barometric_pressure,
            this.fraction_helium[this.mix_number - 1],
            this.fraction_nitrogen[this.mix_number - 1],
            P === 0
              ? this.descentppO2
              : this.fraction_pO2SetPoint[this.mix_number - 1],
            this.fraction_useDiluentGas[this.mix_number - 1],
            this.segment_time,
          );
          if (t) this.run_bailout = true;
          this.outputProfileMixO2[this.outputProfileCounter][
            this.current_dive_number
          ] = e.fraction_oxygen;
          this.outputProfileMixHe[this.outputProfileCounter][
            this.current_dive_number
          ] = e.fraction_helium;
          this.addInspiredGasRuntime(
            this.fraction_helium[this.mix_number - 1],
            this.fraction_nitrogen[this.mix_number - 1],
            this.segment_time,
          );
          this.outputProfileCounter++;
        }
        x = this.profileDepth[_][this.current_dive_number];
        h += this.profileTime[_][this.current_dive_number];
        if (_ > 0) {
          if (
            this.profileDepth[_][this.current_dive_number] <
            this.profileDepth[_ - 1][this.current_dive_number]
          )
            h += Math.floor(
              (this.profileDepth[_][this.current_dive_number] -
                this.profileDepth[_ - 1][this.current_dive_number]) /
                this.profileDecAccSpeed[_][this.current_dive_number],
            );
        }
        this.mix_number = this.profileMix[_][this.current_dive_number] + 1;
        this.gas_loadings_constant_depth(x, h);
        V = d;
        _++;
        this.outputProfileDepth[this.outputProfileCounter][
          this.current_dive_number
        ] = x;
        this.outputProfileTime[this.outputProfileCounter][
          this.current_dive_number
        ] = this.run_time;
        this.outputProfileSegmentTime[this.outputProfileCounter][
          this.current_dive_number
        ] = this.segment_time;
        this.outputProfileSegmentType[this.outputProfileCounter][
          this.current_dive_number
        ] = "bottom";
        let t = this.calc_inspired_gas(
          x + this.barometric_pressure,
          this.fraction_helium[this.mix_number - 1],
          this.fraction_nitrogen[this.mix_number - 1],
          this.fraction_pO2SetPoint[this.mix_number - 1],
          this.fraction_useDiluentGas[this.mix_number - 1],
          this.segment_time,
        );
        this.outputProfileMixO2[this.outputProfileCounter][
          this.current_dive_number
        ] = t.fraction_oxygen;
        this.outputProfileMixHe[this.outputProfileCounter][
          this.current_dive_number
        ] = t.fraction_helium;
        this.addInspiredGasRuntime(
          this.fraction_helium[this.mix_number - 1],
          this.fraction_nitrogen[this.mix_number - 1],
          this.segment_time,
        );
        this.outputProfileGas[this.outputProfileCounter][
          this.current_dive_number
        ] = this.mix_number - 1;
        M = this.calc_start_of_deco_zone(x, this.finalAscentSpeed);
        if (this.units_equal_fsw) {
          if (this.decoStepSize < 10) {
            U = M / this.decoStepSize - 0.5;
            m = Math.round(U) * this.decoStepSize;
          } else {
            U = M / 10 - 0.5;
            m = Math.round(U) * 10;
          }
        }
        if (this.units_equal_msw) {
          if (this.decoStepSize < 3) {
            U = M / this.decoStepSize - 0.5;
            m = Math.round(U) * this.decoStepSize;
          } else {
            U = M / 3 - 0.5;
            m = Math.round(U) * 3;
          }
        }
        this.outputProfileCounter++;
      }
      if (d > 0 && _ > 0) {
        this.firstDecoProfilePoint = this.outputProfileCounter - 1;
      }
      this.nuclear_regeneration(this.run_time);
      this.calc_initial_allowable_gradient();
      for (_ = 1; _ <= 16; ++_) {
        g[_ - 1] = this.helium_pressure[_ - 1];
        u[_ - 1] = this.nitrogen_pressure[_ - 1];
      }
      T = this.run_time;
      $ = this.segment_number;
      E = H + 1;
      l[0] = V;
      O[0] = this.mix_number;
      F[0] = this.finalAscentSpeed;
      w[0] = this.decoStepSize;
      for (_ = 1; _ <= H; _++) {
        l[_] = this.decoMOD[_ - 1][this.current_dive_number];
        O[_] = W + _;
        F[_] = this.finalAscentSpeed;
        w[_] = this.decoStepSize;
      }
      if (this.lastStop6m20ft) {
        for (_ = 1; _ <= H; _++) {
          if (l[_] == 2 * this.decoStepSize) w[_] = 2 * this.decoStepSize;
        }
        if (_ >= H) {
          l[_] = 2 * this.decoStepSize;
          O[_] = O[_ - 1];
          F[_] = this.finalAscentSpeed;
          w[_] = 2 * this.decoStepSize;
          E++;
        }
      }
      P = l[0];
      this.mix_number = O[0];
      c = F[0];
      S = w[0];
      M = this.calc_start_of_deco_zone(P, c);
      this.outputStartOfDecoDepth[this.current_dive_number] = M;
      if (this.units_equal_fsw) {
        if (S < 10) {
          U = M / S - 0.5;
          m = Math.round(U) * S;
        } else {
          U = M / 10 - 0.5;
          m = Math.round(U) * 10;
        }
      }
      if (this.units_equal_msw) {
        if (S < 3) {
          U = M / S - 0.5;
          m = Math.round(U) * S;
        } else {
          U = M / 3 - 0.5;
          m = Math.round(U) * 3;
        }
      }
      this.gas_loadings_ascent_descent(P, M, c);
      p = this.run_time;
      N = 0;
      k = 0;
      R = false;
      for (_ = 1; _ <= 16; ++_) {
        j[_ - 1] = 0;
        G[_ - 1] = this.helium_pressure[_ - 1];
        L[_ - 1] = this.nitrogen_pressure[_ - 1];
        this.max_actual_gradient[_ - 1] = 0;
      }
      while (true) {
        this.calc_ascent_ceiling();
        if (this.ascent_ceiling_depth <= 0) {
          this.deco_stop_depth = 0;
        } else {
          B = this.ascent_ceiling_depth / S + 0.5;
          this.deco_stop_depth = Math.round(B) * S;
        }
        if (this.deco_stop_depth > M) {
          return -1;
        }
        this.projected_ascent(M, c, S);
        if (this.deco_stop_depth > M) {
          return -1;
        }
        if (this.deco_stop_depth == 0) {
          for (_ = 1; _ <= 16; ++_) {
            this.helium_pressure[_ - 1] = g[_ - 1];
            this.nitrogen_pressure[_ - 1] = u[_ - 1];
          }
          this.run_time = T;
          this.segment_number = $;
          P = l[0];
          d = 0;
          this.gas_loadings_ascent_descent(P, d, c);
          break;
        }
        P = M;
        let t = 0;
        if (
          this.profileDepth[this.firstDecoProfilePoint][
            this.current_dive_number
          ] >= this.deco_stop_depth &&
          this.profileDepth[this.firstDecoProfilePoint][
            this.current_dive_number
          ] > 0
        ) {
          this.deco_stop_depth =
            this.profileDepth[this.firstDecoProfilePoint][
              this.current_dive_number
            ];
          q =
            this.profileTime[this.firstDecoProfilePoint][
              this.current_dive_number
            ];
          this.mix_number =
            this.profileMix[this.firstDecoProfilePoint][
              this.current_dive_number
            ] + 1;
          c =
            this.profileDecAccSpeed[this.firstDecoProfilePoint][
              this.current_dive_number
            ];
          t++;
          Y = false;
        }
        y = this.deco_stop_depth;
        while (true) {
          this.gas_loadings_ascent_descent(P, this.deco_stop_depth, c);
          if (this.deco_stop_depth <= 0) {
            break;
          }
          if (Y) {
            if (E > 1) {
              r = E;
              for (_ = 2; _ <= r; ++_) {
                if (l[_ - 1] == this.deco_stop_depth)
                  q = Math.max(this.deco_gas_switch_time, q);
                if (l[_ - 1] >= this.deco_stop_depth) {
                  this.mix_number = O[_ - 1];
                  c = F[_ - 1];
                  S = w[_ - 1];
                }
              }
            }
          }
          Y = true;
          this.next_deco_stop_depth = this.deco_stop_depth - S;
          this.next_deco_stop_depth = this.roundDecoStop(
            this.next_deco_stop_depth,
            S,
          );
          if (
            this.profileDepth[this.firstDecoProfilePoint + t][
              this.current_dive_number
            ] >=
              this.next_deco_stop_depth - S / 2 &&
            this.profileDepth[this.firstDecoProfilePoint + t][
              this.current_dive_number
            ] > 0
          ) {
            if (
              this.profileDepth[this.firstDecoProfilePoint + t][
                this.current_dive_number
              ] >
              this.profileDepth[this.firstDecoProfilePoint + t - 1][
                this.current_dive_number
              ]
            )
              return -(
                this.firstDecoProfilePoint +
                t +
                100 * this.current_dive_number
              );
            this.next_deco_stop_depth =
              this.profileDepth[this.firstDecoProfilePoint + t][
                this.current_dive_number
              ];
            this.boyles_law_compensation(
              y,
              this.deco_stop_depth,
              this.deco_stop_depth - this.next_deco_stop_depth,
            );
            this.decompression_stop(
              this.deco_stop_depth,
              this.deco_stop_depth - this.next_deco_stop_depth,
              0,
              q,
            );
            q =
              this.profileTime[this.firstDecoProfilePoint + t][
                this.current_dive_number
              ];
            this.mix_number =
              this.profileMix[this.firstDecoProfilePoint + t][
                this.current_dive_number
              ] + 1;
            c =
              this.profileDecAccSpeed[this.firstDecoProfilePoint + t][
                this.current_dive_number
              ];
            t++;
            Y = false;
          } else {
            this.boyles_law_compensation(
              y,
              this.deco_stop_depth,
              this.deco_stop_depth - this.next_deco_stop_depth,
            );
            this.decompression_stop(
              this.deco_stop_depth,
              this.deco_stop_depth - this.next_deco_stop_depth,
              0,
              q,
            );
            q = 0;
          }
          if (this.next_deco_stop_depth < 0) this.next_deco_stop_depth = 0;
          P = this.deco_stop_depth;
          k = this.run_time;
          this.deco_stop_depth = this.next_deco_stop_depth;
        }
        N = this.run_time - p;
        this.calc_surface_phase_volume_time();
        for (_ = 1; _ <= 16; ++_) {
          I[_ - 1] = N + this.surface_phase_volume_time[_ - 1];
          z = Math.abs((o = I[_ - 1] - j[_ - 1]));
          if (z <= 1) {
            R = true;
          }
        }
        if (R || D) {
          for (_ = 1; _ <= 16; ++_) {
            this.helium_pressure[_ - 1] = g[_ - 1];
            this.nitrogen_pressure[_ - 1] = u[_ - 1];
          }
          this.run_time = T;
          this.segment_number = $;
          P = l[0];
          this.mix_number = O[0];
          c = F[0];
          S = w[0];
          this.deco_stop_depth = y;
          k = 0;
          t = 0;
          if (
            this.profileDepth[this.firstDecoProfilePoint][
              this.current_dive_number
            ] == this.deco_stop_depth
          ) {
            q =
              this.profileTime[this.firstDecoProfilePoint][
                this.current_dive_number
              ];
            this.mix_number =
              this.profileMix[this.firstDecoProfilePoint][
                this.current_dive_number
              ] + 1;
            c =
              this.profileDecAccSpeed[this.firstDecoProfilePoint][
                this.current_dive_number
              ];
            t++;
            Y = false;
          }
          while (true) {
            this.calc_max_actual_gradient(this.deco_stop_depth);
            this.gas_loadings_ascent_descent(P, this.deco_stop_depth, c);
            if (this.deco_stop_depth <= 0) {
              break;
            }
            if (Y) {
              if (E > 1) {
                r = E;
                for (_ = 2; _ <= r; ++_) {
                  if (l[_ - 1] == this.deco_stop_depth)
                    q = Math.max(this.deco_gas_switch_time, q);
                  if (l[_ - 1] >= this.deco_stop_depth) {
                    this.mix_number = O[_ - 1];
                    c = F[_ - 1];
                    S = w[_ - 1];
                  }
                }
              }
            }
            Y = true;
            this.next_deco_stop_depth = this.deco_stop_depth - S;
            this.next_deco_stop_depth = this.roundDecoStop(
              this.next_deco_stop_depth,
              S,
            );
            if (
              this.profileDepth[this.firstDecoProfilePoint + t][
                this.current_dive_number
              ] >=
                this.next_deco_stop_depth - S / 2 &&
              this.profileDepth[this.firstDecoProfilePoint + t][
                this.current_dive_number
              ] > 0
            ) {
              if (
                this.profileDepth[this.firstDecoProfilePoint + t][
                  this.current_dive_number
                ] >
                this.profileDepth[this.firstDecoProfilePoint + t - 1][
                  this.current_dive_number
                ]
              )
                return -(
                  this.firstDecoProfilePoint +
                  t +
                  100 * this.current_dive_number
                );
              this.next_deco_stop_depth =
                this.profileDepth[this.firstDecoProfilePoint + t][
                  this.current_dive_number
                ];
              this.boyles_law_compensation(
                y,
                this.deco_stop_depth,
                this.deco_stop_depth - this.next_deco_stop_depth,
              );
              this.decompression_stop(
                this.deco_stop_depth,
                this.deco_stop_depth - this.next_deco_stop_depth,
                0,
                q,
              );
              q =
                this.profileTime[this.firstDecoProfilePoint + t][
                  this.current_dive_number
                ];
              if (k == 0) {
                o = this.segment_time / this.minimum_deco_stop_time + 0.5;
                A = Math.round(o) * this.minimum_deco_stop_time;
              } else {
                A = this.run_time - k;
              }
              let e = this.calc_inspired_gas(
                this.deco_stop_depth + this.barometric_pressure,
                this.fraction_helium[this.mix_number - 1],
                this.fraction_nitrogen[this.mix_number - 1],
                this.fraction_pO2SetPoint[this.mix_number - 1],
                this.fraction_useDiluentGas[this.mix_number - 1],
                A,
              );
              this.outputProfileMixO2[this.outputProfileCounter][
                this.current_dive_number
              ] = e.fraction_oxygen;
              this.outputProfileMixHe[this.outputProfileCounter][
                this.current_dive_number
              ] = e.fraction_helium;
              this.outputProfileGas[this.outputProfileCounter][
                this.current_dive_number
              ] = this.mix_number - 1;
              this.mix_number =
                this.profileMix[this.firstDecoProfilePoint + t][
                  this.current_dive_number
                ] + 1;
              c =
                this.profileDecAccSpeed[this.firstDecoProfilePoint + t][
                  this.current_dive_number
                ];
              t++;
              Y = false;
            } else {
              this.boyles_law_compensation(
                y,
                this.deco_stop_depth,
                this.deco_stop_depth - this.next_deco_stop_depth,
              );
              this.decompression_stop(
                this.deco_stop_depth,
                this.deco_stop_depth - this.next_deco_stop_depth,
                0,
                q,
              );
              q = 0;
              if (k == 0) {
                o = this.segment_time / this.minimum_deco_stop_time + 0.5;
                A = Math.round(o) * this.minimum_deco_stop_time;
              } else {
                A = this.run_time - k;
              }
              let t = this.calc_inspired_gas(
                this.deco_stop_depth + this.barometric_pressure,
                this.fraction_helium[this.mix_number - 1],
                this.fraction_nitrogen[this.mix_number - 1],
                this.fraction_pO2SetPoint[this.mix_number - 1],
                this.fraction_useDiluentGas[this.mix_number - 1],
                A,
              );
              this.outputProfileMixO2[this.outputProfileCounter][
                this.current_dive_number
              ] = t.fraction_oxygen;
              this.outputProfileMixHe[this.outputProfileCounter][
                this.current_dive_number
              ] = t.fraction_helium;
              this.outputProfileGas[this.outputProfileCounter][
                this.current_dive_number
              ] = this.mix_number - 1;
            }
            this.outputProfileDepth[this.outputProfileCounter][
              this.current_dive_number
            ] = this.deco_stop_depth;
            this.outputProfileTime[this.outputProfileCounter][
              this.current_dive_number
            ] = this.run_time;
            this.outputProfileSegmentTime[this.outputProfileCounter][
              this.current_dive_number
            ] = A;
            this.addInspiredGasRuntime(
              this.fraction_helium[this.mix_number - 1],
              this.fraction_nitrogen[this.mix_number - 1],
              A,
            );
            if (this.outputProfileCounter == this.firstDecoProfilePoint + 1) {
              this.outputProfileSegmentType[this.outputProfileCounter][
                this.current_dive_number
              ] = "first_ascent";
            }
            this.outputProfileCounter++;
            this.outputProfileSegmentType[this.outputProfileCounter][
              this.current_dive_number
            ] = Y ? "ascent" : "bottom";
            this.outputProfileDepth[this.outputProfileCounter][
              this.current_dive_number
            ] = -1;
            P = this.deco_stop_depth;
            k = this.run_time;
            this.deco_stop_depth = this.next_deco_stop_depth;
          }
          break;
        } else {
          this.critical_volume(N);
          N = 0;
          this.run_time = p;
          P = M;
          this.mix_number = O[0];
          c = F[0];
          S = w[0];
          for (_ = 1; _ <= 16; ++_) {
            j[_ - 1] = I[_ - 1];
            this.helium_pressure[_ - 1] = G[_ - 1];
            this.nitrogen_pressure[_ - 1] = L[_ - 1];
          }
          continue;
        }
      }
      if (this.current_dive_number++ >= this.dive_no) break;
      C = this.surfaceIntervals[this.current_dive_number];
      this.gas_loadings_surface_interval(C);
      this.vpm_repetitive_algorithm(C);
      for (_ = 1; _ <= 16; ++_) {
        this.max_crushing_pressure_he[_ - 1] = 0;
        this.max_crushing_pressure_n2[_ - 1] = 0;
        this.max_actual_gradient[_ - 1] = 0;
      }
      this.run_time = 0;
      this.segment_number = 0;
    }
    this.decoProfileCalculated = true;
    return 0;
  }
  schreiner_equation__(t, e, i, n, s) {
    let r;
    r = t + e * (i - 1 / n) - (t - s - e / n) * Math.exp(-n * i);
    return r;
  }
  haldane_equation__(t, e, i, n) {
    let s;
    s = t + (e - t) * (1 - Math.exp(-i * n));
    return s;
  }
  calc_inspired_gas(t, e, i, n, s, r) {
    if (
      this.run_bailout &&
      t - this.barometric_pressure <
        this.minimum_profile_depth[this.current_dive_number]
    ) {
      n = 0;
    }
    if (!e || isNaN(e)) e = 0;
    if (!i || isNaN(i)) i = 0;
    let o = 1 - e - i;
    let a = t - this.barometric_pressure;
    if (this.configuration == "CCR" && n != 0) {
      let t = s ? e + i : this.fraction_helium[0] + this.fraction_nitrogen[0];
      let r = (s ? e : this.fraction_helium[0]) / t;
      let h = (s ? i : this.fraction_nitrogen[0]) / t;
      let c = n / PI.depth2press(a);
      let u = 1 - c;
      let l = u * r;
      let f = u * h;
      if (c > 1);
      else {
        e = l;
        i = f;
        o = c;
      }
    } else if (this.configuration == "pSCR" && n != 0) {
      if (o < 1 && r > 0) {
        let t = new ZI(this.rmv, this.metabolic_o2_consumption);
        let n =
          (this.outputProfileGasRuntime[this.current_dive_number][e + "/" + i]
            ? this.outputProfileGasRuntime[this.current_dive_number][
                e + "/" + i
              ]
            : 0) + r;
        let s = t.PFavg(a, n, o * 100);
        let h = s / PI.depth2press(a);
        let c = 1 - h;
        let u = e / (e + i);
        let l = i / (e + i);
        let f = c * u;
        let d = c * l;
        if (s >= 0.16) {
          e = f;
          i = d;
          o = h;
        }
      }
    } else;
    return { fraction_oxygen: o, fraction_helium: e, fraction_nitrogen: i };
  }
  gas_loadings_ascent_descent(t, e, i) {
    let n, s;
    let r, o, a, h, c;
    let u;
    this.segment_time = (e - t) / i;
    h = this.run_time;
    this.run_time = h + this.segment_time;
    n = this.segment_number;
    this.segment_number = n + 1;
    this.ending_ambient_pressure = e + this.barometric_pressure;
    c = t + this.barometric_pressure;
    let l = e - (e - t) / 2;
    let f = this.calc_inspired_gas(
      l + this.barometric_pressure,
      this.fraction_helium[this.mix_number - 1],
      this.fraction_nitrogen[this.mix_number - 1],
      this.fraction_pO2SetPoint[this.mix_number - 1],
      this.fraction_useDiluentGas[this.mix_number - 1],
      1,
    );
    o = (c - this.water_vapor_pressure) * f.fraction_helium;
    r = (c - this.water_vapor_pressure) * f.fraction_nitrogen;
    u = i * f.fraction_helium;
    a = i * f.fraction_nitrogen;
    for (s = 1; s <= 16; ++s) {
      this.initial_helium_pressure[s - 1] = this.helium_pressure[s - 1];
      this.initial_nitrogen_pressure[s - 1] = this.nitrogen_pressure[s - 1];
      this.helium_pressure[s - 1] = this.schreiner_equation__(
        o,
        u,
        this.segment_time,
        this.helium_time_constant[s - 1],
        this.initial_helium_pressure[s - 1],
      );
      this.nitrogen_pressure[s - 1] = this.schreiner_equation__(
        r,
        a,
        this.segment_time,
        this.nitrogen_time_constant[s - 1],
        this.initial_nitrogen_pressure[s - 1],
      );
    }
    return 0;
  }
  calc_crushing_pressure(t, e, i) {
    let n, s;
    let r, o, a, h;
    let c,
      u,
      l,
      f = 0;
    let d;
    let p,
      m,
      g,
      v,
      w = 0,
      _,
      b,
      y,
      x,
      M,
      T,
      E;
    let A, S, k, I, C, O, D, R, P;
    m = this.gradient_onset_of_imperm_atm * this.units_factor;
    h = this.gradient_onset_of_imperm_atm * 101325;
    T = t + this.barometric_pressure;
    a = e + this.barometric_pressure;
    for (d = 1; d <= 16; ++d) {
      g =
        this.initial_helium_pressure[d - 1] +
        this.initial_nitrogen_pressure[d - 1] +
        this.constant_pressure_other_gases;
      x = T - g;
      E =
        this.helium_pressure[d - 1] +
        this.nitrogen_pressure[d - 1] +
        this.constant_pressure_other_gases;
      C = a - E;
      M =
        1 /
        (h / ((this.skin_compression_gammac - this.surface_tension_gamma) * 2) +
          1 / this.adjusted_critical_radius_he[d - 1]);
      y =
        1 /
        (h / ((this.skin_compression_gammac - this.surface_tension_gamma) * 2) +
          1 / this.adjusted_critical_radius_n2[d - 1]);
      if (C <= m) {
        w = a - E;
        f = a - E;
      }
      if (C > m) {
        if (x == m) {
          this.amb_pressure_onset_of_imperm[d - 1] = T;
          this.gas_tension_onset_of_imperm[d - 1] = g;
        }
        if (x < m) {
          this.onset_of_impermeability(T, a, i, d);
        }
        A = (a / this.units_factor) * 101325;
        _ =
          (this.amb_pressure_onset_of_imperm[d - 1] / this.units_factor) *
          101325;
        O =
          (this.gas_tension_onset_of_imperm[d - 1] / this.units_factor) *
          101325;
        R = (this.skin_compression_gammac - this.surface_tension_gamma) * 2;
        D =
          A -
          _ +
          O +
          ((this.skin_compression_gammac - this.surface_tension_gamma) * 2) / M;
        n = M;
        P = O * (n * (n * n));
        v = M;
        c = R / D;
        u = this.radius_root_finder(D, R, P, c, v);
        n = M;
        s = u;
        b = h + A - _ + O * (1 - (n * (n * n)) / (s * (s * s)));
        w = (b / 101325) * this.units_factor;
        k = (this.skin_compression_gammac - this.surface_tension_gamma) * 2;
        S =
          A -
          _ +
          O +
          ((this.skin_compression_gammac - this.surface_tension_gamma) * 2) / y;
        n = y;
        I = O * (n * (n * n));
        l = y;
        r = k / S;
        o = this.radius_root_finder(S, k, I, r, l);
        n = y;
        s = o;
        p = h + A - _ + O * (1 - (n * (n * n)) / (s * (s * s)));
        f = (p / 101325) * this.units_factor;
      }
      n = this.max_crushing_pressure_he[d - 1];
      this.max_crushing_pressure_he[d - 1] = Math.max(n, w);
      n = this.max_crushing_pressure_n2[d - 1];
      this.max_crushing_pressure_n2[d - 1] = Math.max(n, f);
    }
    return 0;
  }
  onset_of_impermeability(t, e, i, n) {
    let s = true;
    let r, o, a;
    let h;
    let c = 0,
      u,
      l,
      f,
      d,
      p,
      m,
      g,
      v,
      w,
      _,
      b,
      y,
      x,
      M;
    let T = 0,
      E,
      A,
      S;
    l = this.gradient_onset_of_imperm_atm * this.units_factor;
    let k = this.calc_inspired_gas(
      t,
      this.fraction_helium[this.mix_number - 1],
      this.fraction_nitrogen[this.mix_number - 1],
      this.fraction_pO2SetPoint[this.mix_number - 1],
      this.fraction_useDiluentGas[this.mix_number - 1],
      1,
    );
    p = (t - this.water_vapor_pressure) * k.fraction_helium;
    u = (t - this.water_vapor_pressure) * k.fraction_nitrogen;
    A = i * k.fraction_helium;
    g = i * k.fraction_nitrogen;
    d = 0;
    _ = (e - t) / i;
    f =
      this.initial_helium_pressure[n - 1] +
      this.initial_nitrogen_pressure[n - 1] +
      this.constant_pressure_other_gases;
    w = t - f - l;
    E = this.schreiner_equation__(
      p,
      A,
      _,
      this.helium_time_constant[n - 1],
      this.initial_helium_pressure[n - 1],
    );
    m = this.schreiner_equation__(
      u,
      g,
      _,
      this.nitrogen_time_constant[n - 1],
      this.initial_nitrogen_pressure[n - 1],
    );
    x = E + m + this.constant_pressure_other_gases;
    M = e - x - l;
    if (M * w >= 0) {
      this.pause();
    }
    if (w < 0) {
      r = d;
      S = _ - d;
    } else {
      r = _;
      S = d - _;
    }
    for (h = 1; h <= 100; ++h) {
      o = S;
      S = o * 0.5;
      y = r + S;
      T = t + i * y;
      b = this.schreiner_equation__(
        p,
        A,
        y,
        this.helium_time_constant[n - 1],
        this.initial_helium_pressure[n - 1],
      );
      a = this.schreiner_equation__(
        u,
        g,
        y,
        this.nitrogen_time_constant[n - 1],
        this.initial_nitrogen_pressure[n - 1],
      );
      c = b + a + this.constant_pressure_other_gases;
      v = T - c - l;
      if (v <= 0) {
        r = y;
      }
      if (Math.abs(S) < 0.001 || v == 0) {
        s = false;
        break;
      }
    }
    if (s) {
      this.pause();
    }
    this.amb_pressure_onset_of_imperm[n - 1] = T;
    this.gas_tension_onset_of_imperm[n - 1] = c;
    return 0;
  }
  radius_root_finder(t, e, i, n, s) {
    let r;
    let o, a, h, c;
    let u;
    let l, f, d, p, m;
    l = n * (n * (t * n - e)) - i;
    d = s * (s * (t * s - e)) - i;
    if (l > 0 && d > 0) {
      this.pause();
    }
    if (l < 0 && d < 0) {
      this.pause();
    }
    if (l == 0) {
      r = n;
      return r;
    } else if (d == 0) {
      r = s;
      return r;
    } else if (l < 0) {
      o = n;
      c = s;
    } else {
      c = n;
      o = s;
    }
    r = (n + s) * 0.5;
    a = Math.abs(s - n);
    m = a;
    h = r * (r * (t * r - e)) - i;
    p = r * (r * 3 * t - e * 2);
    for (u = 1; u <= 100; ++u) {
      if (
        ((r - c) * p - h) * ((r - o) * p - h) >= 0 ||
        Math.abs(h * 2) > Math.abs(a * p)
      ) {
        a = m;
        m = (c - o) * 0.5;
        r = o + m;
        if (o == r) {
          return r;
        }
      } else {
        a = m;
        m = h / p;
        f = r;
        r -= m;
        if (f == r) {
          return r;
        }
      }
      if (Math.abs(m) < 1e-12) {
        return r;
      }
      h = r * (r * (t * r - e)) - i;
      p = r * (r * 3 * t - e * 2);
      if (h < 0) {
        o = r;
      } else {
        c = r;
      }
    }
    this.pause();
    return 0;
  }
  gas_loadings_constant_depth(t, e) {
    let i;
    let n;
    let s;
    let r;
    let o, a, h, c;
    this.segment_time = e - this.run_time;
    h = e;
    this.run_time = h;
    n = this.segment_number;
    this.segment_number = n + 1;
    o = t + this.barometric_pressure;
    let u = this.calc_inspired_gas(
      o,
      this.fraction_helium[this.mix_number - 1],
      this.fraction_nitrogen[this.mix_number - 1],
      this.fraction_pO2SetPoint[this.mix_number - 1],
      this.fraction_useDiluentGas[this.mix_number - 1],
      this.segment_time,
    );
    a = (o - this.water_vapor_pressure) * u.fraction_helium;
    i = (o - this.water_vapor_pressure) * u.fraction_nitrogen;
    this.ending_ambient_pressure = o;
    for (r = 1; r <= 16; ++r) {
      s = this.helium_pressure[r - 1];
      c = this.nitrogen_pressure[r - 1];
      this.helium_pressure[r - 1] = this.haldane_equation__(
        s,
        a,
        this.helium_time_constant[r - 1],
        this.segment_time,
      );
      this.nitrogen_pressure[r - 1] = this.haldane_equation__(
        c,
        i,
        this.nitrogen_time_constant[r - 1],
        this.segment_time,
      );
    }
    return;
  }
  nuclear_regeneration(t) {
    let e, i, n;
    let s;
    let r, o, a, h, c;
    for (s = 1; s <= 16; ++s) {
      o = (this.max_crushing_pressure_he[s - 1] / this.units_factor) * 101325;
      r = (this.max_crushing_pressure_n2[s - 1] / this.units_factor) * 101325;
      n =
        1 /
        (o / ((this.skin_compression_gammac - this.surface_tension_gamma) * 2) +
          1 / this.adjusted_critical_radius_he[s - 1]);
      i =
        1 /
        (r / ((this.skin_compression_gammac - this.surface_tension_gamma) * 2) +
          1 / this.adjusted_critical_radius_n2[s - 1]);
      this.regenerated_radius_he[s - 1] =
        this.adjusted_critical_radius_he[s - 1] +
        (n - this.adjusted_critical_radius_he[s - 1]) *
          Math.exp(-t / this.regeneration_time_constant);
      this.regenerated_radius_n2[s - 1] =
        this.adjusted_critical_radius_n2[s - 1] +
        (i - this.adjusted_critical_radius_n2[s - 1]) *
          Math.exp(-t / this.regeneration_time_constant);
      e =
        (n *
          (this.adjusted_critical_radius_he[s - 1] -
            this.regenerated_radius_he[s - 1])) /
        (this.regenerated_radius_he[s - 1] *
          (this.adjusted_critical_radius_he[s - 1] - n));
      c =
        (i *
          (this.adjusted_critical_radius_n2[s - 1] -
            this.regenerated_radius_n2[s - 1])) /
        (this.regenerated_radius_n2[s - 1] *
          (this.adjusted_critical_radius_n2[s - 1] - i));
      h = o * e;
      a = r * c;
      this.adjusted_crushing_pressure_he[s - 1] =
        (h / 101325) * this.units_factor;
      this.adjusted_crushing_pressure_n2[s - 1] =
        (a / 101325) * this.units_factor;
    }
    return 0;
  }
  calc_initial_allowable_gradient() {
    let t, e;
    let i;
    for (i = 1; i <= 16; ++i) {
      t =
        (this.surface_tension_gamma *
          2 *
          (this.skin_compression_gammac - this.surface_tension_gamma)) /
        (this.regenerated_radius_n2[i - 1] * this.skin_compression_gammac);
      e =
        (this.surface_tension_gamma *
          2 *
          (this.skin_compression_gammac - this.surface_tension_gamma)) /
        (this.regenerated_radius_he[i - 1] * this.skin_compression_gammac);
      this.initial_allowable_gradient_n2[i - 1] =
        (t / 101325) * this.units_factor;
      this.initial_allowable_gradient_he[i - 1] =
        (e / 101325) * this.units_factor;
      this.allowable_gradient_he[i - 1] =
        this.initial_allowable_gradient_he[i - 1];
      this.allowable_gradient_n2[i - 1] =
        this.initial_allowable_gradient_n2[i - 1];
    }
    return 0;
  }
  calc_ascent_ceiling() {
    let t, e;
    let i;
    let n;
    let s = new Array(),
      r,
      o;
    for (n = 1; n <= 16; ++n) {
      r = this.helium_pressure[n - 1] + this.nitrogen_pressure[n - 1];
      if (r > 0) {
        let t = this.VPM_GFS ? this.VPM_gf_high / 100 : 1;
        i =
          (this.allowable_gradient_he[n - 1] * this.helium_pressure[n - 1] +
            this.allowable_gradient_n2[n - 1] * this.nitrogen_pressure[n - 1]) /
          r;
        o = r + this.constant_pressure_other_gases - i * t;
      } else {
        t = this.allowable_gradient_he[n - 1];
        e = this.allowable_gradient_n2[n - 1];
        i = Math.min(t, e);
        o = this.constant_pressure_other_gases - i;
      }
      if (o < 0) {
        o = 0;
      }
      s[n - 1] = o - this.barometric_pressure;
    }
    this.ascent_ceiling_depth = s[0];
    for (n = 2; n <= 16; ++n) {
      t = this.ascent_ceiling_depth;
      e = s[n - 1];
      this.ascent_ceiling_depth = Math.max(t, e);
    }
    return 0;
  }
  calc_max_actual_gradient(t) {
    let e;
    let i;
    let n;
    for (i = 1; i <= 16; ++i) {
      n =
        this.helium_pressure[i - 1] +
        this.nitrogen_pressure[i - 1] +
        this.constant_pressure_other_gases -
        (t + this.barometric_pressure);
      if (n <= 0) {
        n = 0;
      }
      e = this.max_actual_gradient[i - 1];
      this.max_actual_gradient[i - 1] = Math.max(e, n);
    }
    return 0;
  }
  calc_surface_phase_volume_time() {
    let t;
    let e;
    let i, n;
    n = (this.barometric_pressure - this.water_vapor_pressure) * 0.79;
    for (e = 1; e <= 16; ++e) {
      if (this.nitrogen_pressure[e - 1] > n) {
        this.surface_phase_volume_time[e - 1] =
          (this.helium_pressure[e - 1] / this.helium_time_constant[e - 1] +
            (this.nitrogen_pressure[e - 1] - n) /
              this.nitrogen_time_constant[e - 1]) /
          (this.helium_pressure[e - 1] + this.nitrogen_pressure[e - 1] - n);
      } else if (
        this.nitrogen_pressure[e - 1] <= n &&
        this.helium_pressure[e - 1] + this.nitrogen_pressure[e - 1] >= n
      ) {
        t =
          (1 /
            (this.nitrogen_time_constant[e - 1] -
              this.helium_time_constant[e - 1])) *
          Math.log(
            (n - this.nitrogen_pressure[e - 1]) / this.helium_pressure[e - 1],
          );
        i =
          (this.helium_pressure[e - 1] / this.helium_time_constant[e - 1]) *
            (1 - Math.exp(-this.helium_time_constant[e - 1] * t)) +
          ((this.nitrogen_pressure[e - 1] - n) /
            this.nitrogen_time_constant[e - 1]) *
            (1 - Math.exp(-this.nitrogen_time_constant[e - 1] * t));
        this.surface_phase_volume_time[e - 1] =
          i / (this.helium_pressure[e - 1] + this.nitrogen_pressure[e - 1] - n);
      } else {
        this.surface_phase_volume_time[e - 1] = 0;
      }
    }
    return 0;
  }
  critical_volume(t) {
    let e;
    let i, n, s, r, o;
    let a;
    let h,
      c = new Array(),
      u,
      l,
      f;
    s = (this.crit_volume_parameter_lambda / 33) * 101325;
    for (a = 1; a <= 16; ++a) {
      c[a - 1] = t + this.surface_phase_volume_time[a - 1];
    }
    for (a = 1; a <= 16; ++a) {
      f =
        (this.adjusted_crushing_pressure_he[a - 1] / this.units_factor) *
        101325;
      n =
        (this.initial_allowable_gradient_he[a - 1] / this.units_factor) *
        101325;
      r =
        n +
        (s * this.surface_tension_gamma) /
          (this.skin_compression_gammac * c[a - 1]);
      o =
        (this.surface_tension_gamma * (this.surface_tension_gamma * (s * f))) /
        (this.skin_compression_gammac *
          (this.skin_compression_gammac * c[a - 1]));
      e = r;
      u = (r + Math.sqrt(e * e - o * 4)) / 2;
      this.allowable_gradient_he[a - 1] = (u / 101325) * this.units_factor;
    }
    for (a = 1; a <= 16; ++a) {
      l =
        (this.adjusted_crushing_pressure_n2[a - 1] / this.units_factor) *
        101325;
      i =
        (this.initial_allowable_gradient_n2[a - 1] / this.units_factor) *
        101325;
      r =
        i +
        (s * this.surface_tension_gamma) /
          (this.skin_compression_gammac * c[a - 1]);
      o =
        (this.surface_tension_gamma * (this.surface_tension_gamma * (s * l))) /
        (this.skin_compression_gammac *
          (this.skin_compression_gammac * c[a - 1]));
      e = r;
      h = (r + Math.sqrt(e * e - o * 4)) / 2;
      this.allowable_gradient_n2[a - 1] = (h / 101325) * this.units_factor;
    }
    return 0;
  }
  calc_start_of_deco_zone(t, e) {
    let i = true;
    let n;
    let s, r, o;
    let a, h;
    let c, u, l, f, d, p, m, g, v, w, _, b, y, x;
    let M, T, E, A;
    n = 0;
    b = t + this.barometric_pressure;
    let S = this.calc_inspired_gas(
      b,
      this.fraction_helium[this.mix_number - 1],
      this.fraction_nitrogen[this.mix_number - 1],
      this.fraction_pO2SetPoint[this.mix_number - 1],
      this.fraction_useDiluentGas[this.mix_number - 1],
      1,
    );
    f = (b - this.water_vapor_pressure) * S.fraction_helium;
    c = (b - this.water_vapor_pressure) * S.fraction_nitrogen;
    E = e * S.fraction_helium;
    p = e * S.fraction_nitrogen;
    l = 0;
    v = (b / e) * -1;
    for (a = 1; a <= 16; ++a) {
      r = this.helium_pressure[a - 1];
      y = this.nitrogen_pressure[a - 1];
      g = r + y + this.constant_pressure_other_gases - b;
      T = this.schreiner_equation__(
        f,
        E,
        v,
        this.helium_time_constant[a - 1],
        r,
      );
      d = this.schreiner_equation__(
        c,
        p,
        v,
        this.nitrogen_time_constant[a - 1],
        y,
      );
      x = T + d + this.constant_pressure_other_gases;
      if (x * g >= 0) {
        this.pause();
      }
      if (g < 0) {
        M = l;
        A = v - l;
      } else {
        M = v;
        A = l - v;
      }
      for (h = 1; h <= 100; ++h) {
        s = A;
        A = s * 0.5;
        _ = M + A;
        w = this.schreiner_equation__(
          f,
          E,
          _,
          this.helium_time_constant[a - 1],
          r,
        );
        o = this.schreiner_equation__(
          c,
          p,
          _,
          this.nitrogen_time_constant[a - 1],
          y,
        );
        m = w + o + this.constant_pressure_other_gases - (b + e * _);
        if (m <= 0) {
          M = _;
        }
        if (Math.abs(A) < 0.001 || m == 0) {
          i = false;
          break;
        }
      }
      if (i) {
        this.pause();
      }
      u = b + e * M - this.barometric_pressure;
      n = Math.max(n, u);
    }
    return n;
  }
  projected_ascent(t, e, i) {
    let n, s;
    let r,
      o = new Array(),
      a = new Array(),
      h;
    let c;
    let u,
      l,
      f,
      d,
      p = new Array(),
      m,
      g,
      v = new Array();
    let w, _;
    l = this.deco_stop_depth + this.barometric_pressure;
    g = t + this.barometric_pressure;
    let b = this.calc_inspired_gas(
      g,
      this.fraction_helium[this.mix_number - 1],
      this.fraction_nitrogen[this.mix_number - 1],
      this.fraction_pO2SetPoint[this.mix_number - 1],
      this.fraction_useDiluentGas[this.mix_number - 1],
      1,
    );
    d = (g - this.water_vapor_pressure) * b.fraction_helium;
    u = (g - this.water_vapor_pressure) * b.fraction_nitrogen;
    w = e * b.fraction_helium;
    m = e * b.fraction_nitrogen;
    for (c = 1; c <= 16; ++c) {
      o[c - 1] = this.helium_pressure[c - 1];
      v[c - 1] = this.nitrogen_pressure[c - 1];
    }
    while (true) {
      let t = false;
      this.ending_ambient_pressure = l;
      h = (this.ending_ambient_pressure - g) / e;
      for (c = 1; c <= 16; ++c) {
        f = this.schreiner_equation__(
          d,
          w,
          h,
          this.helium_time_constant[c - 1],
          o[c - 1],
        );
        _ = this.schreiner_equation__(
          u,
          m,
          h,
          this.nitrogen_time_constant[c - 1],
          v[c - 1],
        );
        a[c - 1] = f + _;
        if (a[c - 1] > 0) {
          r =
            (this.allowable_gradient_he[c - 1] * f +
              this.allowable_gradient_n2[c - 1] * _) /
            a[c - 1];
        } else {
          n = this.allowable_gradient_he[c - 1];
          s = this.allowable_gradient_n2[c - 1];
          r = Math.min(n, s);
        }
        p[c - 1] =
          this.ending_ambient_pressure + r - this.constant_pressure_other_gases;
      }
      for (c = 1; c <= 16; ++c) {
        if (a[c - 1] > p[c - 1]) {
          l = this.ending_ambient_pressure + i;
          this.deco_stop_depth += i;
        } else {
          t = true;
          break;
        }
      }
      if (t) break;
    }
    return 0;
  }
  boyles_law_compensation(t, e, i) {
    let n;
    let s;
    let r, o;
    let a, h;
    let c, u, l, f, d, p;
    let m;
    let g, v;
    let w, _;
    let b = new Array(),
      y = new Array();
    let x = new Array(),
      M = new Array();
    s = e - i;
    r = t + this.barometric_pressure;
    o = s + this.barometric_pressure;
    a = (r / this.units_factor) * 101325;
    h = (o / this.units_factor) * 101325;
    for (n = 1; n <= 16; ++n) {
      g = (this.allowable_gradient_he[n - 1] / this.units_factor) * 101325;
      v = (2 * this.surface_tension_gamma) / g;
      b[n - 1] = v;
      c = h;
      u = -2 * this.surface_tension_gamma;
      l = (a + (2 * this.surface_tension_gamma) / v) * v * (v * v);
      f = v;
      d = v * this.cbrtf(a / h);
      p = this.radius_root_finder(c, u, l, f, d);
      y[n - 1] = p;
      m = (2 * this.surface_tension_gamma) / p;
      this.deco_gradient_he[n - 1] = (m / 101325) * this.units_factor;
    }
    for (n = 1; n <= 16; ++n) {
      w = (this.allowable_gradient_n2[n - 1] / this.units_factor) * 101325;
      _ = (2 * this.surface_tension_gamma) / w;
      x[n - 1] = _;
      c = h;
      u = -2 * this.surface_tension_gamma;
      l = (a + (2 * this.surface_tension_gamma) / _) * _ * (_ * _);
      f = _;
      d = _ * this.cbrtf(a / h);
      p = this.radius_root_finder(c, u, l, f, d);
      M[n - 1] = p;
      m = (2 * this.surface_tension_gamma) / p;
      this.deco_gradient_n2[n - 1] = (m / 101325) * this.units_factor;
    }
    return 0;
  }
  decompression_stop(t, e, i, n) {
    let s;
    let r;
    let o;
    let a,
      h = new Array();
    let c;
    let u;
    let l;
    let f, d, p, m;
    let g = new Array(),
      v;
    p = this.run_time;
    s = p / this.minimum_deco_stop_time + 0.5;
    v = Math.round(s) * this.minimum_deco_stop_time;
    this.segment_time = v - this.run_time;
    this.run_time = v;
    m = this.segment_time;
    o = this.segment_number;
    this.segment_number = o + 1;
    l = t + this.barometric_pressure;
    this.ending_ambient_pressure = l;
    d = t - e;
    let w = this;
    function _(t) {
      return w.calc_inspired_gas(
        l,
        w.fraction_helium[w.mix_number - 1],
        w.fraction_nitrogen[w.mix_number - 1],
        w.fraction_pO2SetPoint[w.mix_number - 1],
        w.fraction_useDiluentGas[w.mix_number - 1],
        t,
      );
    }
    let b = _(this.segment_time);
    f = (l - this.water_vapor_pressure) * b.fraction_helium;
    r = (l - this.water_vapor_pressure) * b.fraction_nitrogen;
    for (u = 1; u <= 16; ++u) {
      if (f + r > 0) {
        a =
          (this.deco_gradient_he[u - 1] * f +
            this.deco_gradient_n2[u - 1] * r) /
          (f + r);
        if (
          f + r + this.constant_pressure_other_gases - a >
          d + this.barometric_pressure
        ) {
          this.exit(1);
        }
      }
    }
    while (true) {
      b = _(this.run_time - p);
      f = (l - this.water_vapor_pressure) * b.fraction_helium;
      r = (l - this.water_vapor_pressure) * b.fraction_nitrogen;
      for (u = 1; u <= 16; ++u) {
        h[u - 1] = this.helium_pressure[u - 1];
        g[u - 1] = this.nitrogen_pressure[u - 1];
        this.helium_pressure[u - 1] = this.haldane_equation__(
          h[u - 1],
          f,
          this.helium_time_constant[u - 1],
          this.segment_time,
        );
        this.nitrogen_pressure[u - 1] = this.haldane_equation__(
          g[u - 1],
          r,
          this.nitrogen_time_constant[u - 1],
          this.segment_time,
        );
      }
      this.calc_deco_ceiling();
      if (this.deco_ceiling_depth > d) {
        this.segment_time = this.minimum_deco_stop_time;
        c = m;
        m = c + this.minimum_deco_stop_time;
        this.run_time = this.run_time + this.minimum_deco_stop_time;
      } else break;
    }
    if (i > 0) {
      this.segment_time = i;
      m += this.segment_time;
      this.run_time += this.segment_time;
      for (u = 1; u <= 16; ++u) {
        h[u - 1] = this.helium_pressure[u - 1];
        g[u - 1] = this.nitrogen_pressure[u - 1];
        this.helium_pressure[u - 1] = this.haldane_equation__(
          h[u - 1],
          f,
          this.helium_time_constant[u - 1],
          this.segment_time,
        );
        this.nitrogen_pressure[u - 1] = this.haldane_equation__(
          g[u - 1],
          r,
          this.nitrogen_time_constant[u - 1],
          this.segment_time,
        );
      }
      this.calc_deco_ceiling();
    }
    if (this.run_time - Math.floor(p) < n) {
      this.segment_time = n - (this.run_time - Math.floor(p));
      m += this.segment_time;
      this.run_time += this.segment_time;
      for (u = 1; u <= 16; ++u) {
        h[u - 1] = this.helium_pressure[u - 1];
        g[u - 1] = this.nitrogen_pressure[u - 1];
        this.helium_pressure[u - 1] = this.haldane_equation__(
          h[u - 1],
          f,
          this.helium_time_constant[u - 1],
          this.segment_time,
        );
        this.nitrogen_pressure[u - 1] = this.haldane_equation__(
          g[u - 1],
          r,
          this.nitrogen_time_constant[u - 1],
          this.segment_time,
        );
      }
      this.calc_deco_ceiling();
    }
    this.segment_time = m;
    return 0;
  }
  gas_loadings_surface_interval(t) {
    let e, i;
    let n;
    let s, r;
    s = 0;
    e = (this.barometric_pressure - this.water_vapor_pressure) * 0.79;
    for (n = 1; n <= 16; ++n) {
      i = this.helium_pressure[n - 1];
      r = this.nitrogen_pressure[n - 1];
      this.helium_pressure[n - 1] = this.haldane_equation__(
        i,
        s,
        this.helium_time_constant[n - 1],
        t,
      );
      this.nitrogen_pressure[n - 1] = this.haldane_equation__(
        r,
        e,
        this.nitrogen_time_constant[n - 1],
        t,
      );
    }
    return 0;
  }
  calc_barometric_pressure(t) {
    let e, i, n, s, r, o, a, h, c, u, l, f, d, p, m;
    m = 6369;
    n = 9.80665;
    i = 28.9644;
    p = 8.31432;
    a = 288.15;
    l = 33;
    f = 10.1325;
    o = -6.5;
    u = (n * i) / p;
    if (this.units_equal_fsw) {
      r = t;
      s = r / 3280.839895;
      h = l;
    } else {
      e = t;
      s = e / 1e3;
      h = f;
    }
    c = (s * m) / (s + m);
    d = a + o * c;
    this.barometric_pressure = h * Math.exp((Math.log(a / d) * u) / o);
    return 0;
  }
  vpm_altitude_dive_algorithm() {
    let t;
    let e, i, n, s, r, o;
    let a;
    let h, c, u, l;
    let f, d, p, m;
    let g, v;
    let w;
    let _, b;
    if (this.units_equal_fsw && this.altitude_of_dive > 3e4) {
      this.exit(1);
    }
    if (this.units_equal_msw && this.altitude_of_dive > 9144) {
      this.exit(1);
    }
    if (
      this.diver_acclimatized_at_altitude == "YES" ||
      this.diver_acclimatized_at_altitude == "yes"
    ) {
      w = true;
    } else {
      w = false;
    }
    s = this.ascent_to_altitude_hours * 60;
    c = this.hours_at_altitude_before_dive * 60;
    if (w) {
      this.calc_barometric_pressure(this.altitude_of_dive);
      for (t = 1; t <= 16; ++t) {
        this.adjusted_critical_radius_n2[t - 1] =
          this.initial_critical_radius_n2[t - 1];
        this.adjusted_critical_radius_he[t - 1] =
          this.initial_critical_radius_he[t - 1];
        this.helium_pressure[t - 1] = 0;
        this.nitrogen_pressure[t - 1] =
          (this.barometric_pressure - this.water_vapor_pressure) * 0.79;
      }
    } else {
      if (
        this.starting_acclimatized_altitude >= this.altitude_of_dive ||
        this.starting_acclimatized_altitude < 0
      ) {
        this.exit(1);
      }
      this.calc_barometric_pressure(this.starting_acclimatized_altitude);
      v = this.barometric_pressure;
      for (t = 1; t <= 16; ++t) {
        this.helium_pressure[t - 1] = 0;
        this.nitrogen_pressure[t - 1] =
          (this.barometric_pressure - this.water_vapor_pressure) * 0.79;
      }
      this.calc_barometric_pressure(this.altitude_of_dive);
      r = this.barometric_pressure;
      l = (v - this.water_vapor_pressure) * 0.79;
      n = (r - v) / s;
      p = n * 0.79;
      for (t = 1; t <= 16; ++t) {
        _ = this.nitrogen_pressure[t - 1];
        this.nitrogen_pressure[t - 1] = this.schreiner_equation__(
          l,
          p,
          s,
          this.nitrogen_time_constant[t - 1],
          _,
        );
        u =
          this.nitrogen_pressure[t - 1] +
          this.constant_pressure_other_gases -
          r;
        d = (u / this.units_factor) * 101325;
        h =
          (this.surface_tension_gamma *
            2 *
            (this.skin_compression_gammac - this.surface_tension_gamma)) /
          (this.initial_critical_radius_he[t - 1] *
            this.skin_compression_gammac);
        if (d > h) {
          b =
            (this.surface_tension_gamma *
              2 *
              (this.skin_compression_gammac - this.surface_tension_gamma)) /
            (d * this.skin_compression_gammac);
          this.adjusted_critical_radius_he[t - 1] =
            this.initial_critical_radius_he[t - 1] +
            (this.initial_critical_radius_he[t - 1] - b) *
              Math.exp(-c / this.regeneration_time_constant);
          this.initial_critical_radius_he[t - 1] =
            this.adjusted_critical_radius_he[t - 1];
        } else {
          o =
            1 /
            (d /
              ((this.surface_tension_gamma - this.skin_compression_gammac) *
                2) +
              1 / this.initial_critical_radius_he[t - 1]);
          m =
            this.initial_critical_radius_he[t - 1] +
            (o - this.initial_critical_radius_he[t - 1]) *
              Math.exp(-c / this.regeneration_time_constant);
          this.initial_critical_radius_he[t - 1] = m;
          this.adjusted_critical_radius_he[t - 1] =
            this.initial_critical_radius_he[t - 1];
        }
        a =
          (this.surface_tension_gamma *
            2 *
            (this.skin_compression_gammac - this.surface_tension_gamma)) /
          (this.initial_critical_radius_n2[t - 1] *
            this.skin_compression_gammac);
        if (d > a) {
          g =
            (this.surface_tension_gamma *
              2 *
              (this.skin_compression_gammac - this.surface_tension_gamma)) /
            (d * this.skin_compression_gammac);
          this.adjusted_critical_radius_n2[t - 1] =
            this.initial_critical_radius_n2[t - 1] +
            (this.initial_critical_radius_n2[t - 1] - g) *
              Math.exp(-c / this.regeneration_time_constant);
          this.initial_critical_radius_n2[t - 1] =
            this.adjusted_critical_radius_n2[t - 1];
        } else {
          i =
            1 /
            (d /
              ((this.surface_tension_gamma - this.skin_compression_gammac) *
                2) +
              1 / this.initial_critical_radius_n2[t - 1]);
          f =
            this.initial_critical_radius_n2[t - 1] +
            (i - this.initial_critical_radius_n2[t - 1]) *
              Math.exp(-c / this.regeneration_time_constant);
          this.initial_critical_radius_n2[t - 1] = f;
          this.adjusted_critical_radius_n2[t - 1] =
            this.initial_critical_radius_n2[t - 1];
        }
      }
      e = (this.barometric_pressure - this.water_vapor_pressure) * 0.79;
      for (t = 1; t <= 16; ++t) {
        _ = this.nitrogen_pressure[t - 1];
        this.nitrogen_pressure[t - 1] = this.haldane_equation__(
          _,
          e,
          this.nitrogen_time_constant[t - 1],
          c,
        );
      }
    }
    return 0;
  }
  exit(t) {
    console.log("exit", t);
  }
  pause() {}
  cbrtf(t) {
    if (t > 0) return Math.exp(Math.log(t) / 3);
    else if (t < 0) return -Math.exp(Math.log(-t) / 3);
    else return 0;
  }
  roundDecoStop(t, e) {
    let i;
    if (this.units_equal_fsw) {
      if (e < 10) {
        i = t / e + 0.5;
        t = Math.floor(i) * e;
      } else {
        i = t / 10 + 0.5;
        t = Math.floor(i) * 10;
      }
    }
    if (this.units_equal_msw) {
      if (e < 3) {
        i = t / e + 0.5;
        t = Math.floor(i) * e;
      } else {
        i = t / 3 + 0.5;
        t = Math.floor(i) * 3;
      }
    }
    if (t < 0) t = 0;
    return t;
  }
}
