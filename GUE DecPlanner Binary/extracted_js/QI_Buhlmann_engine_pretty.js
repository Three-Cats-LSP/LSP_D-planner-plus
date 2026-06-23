class QI_extracted {
  constructor() {
    this.MODEL_VALIDATION_SUCCESS = 0;
    this.MODEL_VALIDATION_FAILED = -1;
    this.METRIC = 0;
    this.IMPERIAL = 1;
    this.PROCESSING_ERROR = false;
    this.COMPS = 16;
    this.pref = new NI();
    this.diveTools = new RI();
    this.bailout = true;
    this.diveIndex = 0;
    this.tissues = [];
    this.unitsString = "Metric";
    this.modelName = "ZHL16B";
    this.setUnits("Metric");
    this.initGradient();
    this.initOxTox();
  }
  setUnits(t) {
    this.pref.setUnitsTo(t == "Metric" ? 0 : 1);
  }
  initGradient() {
    this.gradient = new WI(this.pref.getGfLow(), this.pref.getGfHigh());
  }
  initOxTox() {
    this.oxTox = new HI();
  }
  getGradient() {
    return this.gradient;
  }
  setGradient(t) {
    this.gradient = t;
  }
  getOxTox() {
    return this.oxTox;
  }
  setOxTox(t) {
    this.oxTox = t;
  }
  getTissues() {
    return this.tissues;
  }
  setTissues(t) {
    this.tissues = t;
  }
  setModel(t, e) {
    this.modelName = t;
    let i;
    this.gradient = new WI(this.pref.getGfLow(), this.pref.getGfHigh());
    this.oxTox = new HI();
    for (i = 0; i < this.COMPS; i++) {
      if (e) this.tissues[i] = new qI(this.pref, this.getAmbientPress());
      this.tissues[i].setPpHe(0);
      this.tissues[i].setPpN2(
        0.79 * (this.getAmbientPress() - this.pref.getPH2O()),
      );
    }
    this.setTimeConstants();
  }
  controlCompartment() {
    let t;
    let e = 0;
    let i = 0;
    let n = 0;
    for (t = 0; t < this.COMPS; t++) {
      n =
        this.tissues[t].getMaxAmb(this.gradient.getGradientFactor()) -
        this.getAmbientPress();
      if (n > i) {
        e = t;
        i = n;
      }
    }
    return e + 1;
  }
  ceiling() {
    let t;
    let e = 0;
    let i = 0;
    for (t = 0; t < this.COMPS; t++) {
      i =
        this.tissues[t].getMaxAmb(this.gradient.getGradientFactor()) -
        this.getAmbientPress();
      if (i > e) e = i;
    }
    return e;
  }
  mValue(t) {
    let e;
    let i = t + this.getAmbientPress();
    let n = 0;
    let s = 0;
    for (e = 0; e < this.COMPS; e++) {
      n = this.tissues[e].getMV(i);
      if (n > s) s = n;
    }
    return s;
  }
  constDepth(t, e, i, n, s, r) {
    let o;
    let a;
    let h;
    let c;
    let u = t + this.getAmbientPress();
    let l;
    if (s > 0) {
      if (i + n > 0)
        c = u - this.pref.getPH2O() - s * this.pref.getPConversion();
      else c = 0;
      if (c > 0) {
        o = (c * i) / (i + n);
        a = (c * n) / (i + n);
      } else {
        o = 0;
        a = 0;
      }
      h = s * this.pref.getPConversion();
      if (h <= t + this.getAmbientPress() && c > 0) this.oxTox.addO2(e, s);
      else
        this.oxTox.addO2(
          e,
          (u - this.pref.getPH2O()) / this.pref.getPConversion(),
        );
    } else {
      o = (u - this.pref.getPH2O()) * i;
      a = (u - this.pref.getPH2O()) * n;
      h = (u - this.pref.getPH2O()) * (1 - i - n);
      if (t == 0) {
        this.oxTox.removeO2(e);
      } else {
        this.oxTox.addO2(e, h / this.pref.getPConversion());
      }
    }
    if (e > 0) {
      for (l = 0; l < this.COMPS; l++) {
        this.tissues[l].constDepth(
          o,
          a,
          e,
          t,
          r,
          1 - i - n,
          i,
          this.bailout,
          h / this.pref.getPConversion(),
          this.diveIndex,
        );
      }
    }
  }
  ascDec(t, e, i, n, s, r) {
    let o;
    let a;
    let h;
    let c;
    let u = Math.abs((e - t) / i);
    let l;
    let f;
    let d = t + this.getAmbientPress();
    let p = e + this.getAmbientPress();
    let m, g;
    if (u > 0) {
      if (r > 0) {
        m = d - r * this.pref.getPConversion() - this.pref.getPH2O();
        g = p - r * this.pref.getPConversion() - this.pref.getPH2O();
        if (m < 0) m = 0;
        if (g < 0) g = 0;
        if (n + s > 0) {
          a = (m * n) / (n + s);
          h = (m * s) / (n + s);
          l = ((g * n) / (n + s) - a) / u;
          f = ((g * s) / (n + s) - h) / u;
        } else {
          a = 0;
          h = 0;
          l = 0;
          f = 0;
        }
        this.oxTox.addO2(u, r);
      } else {
        a = (d - this.pref.getPH2O()) * n;
        h = (d - this.pref.getPH2O()) * s;
        l = i * n;
        f = i * s;
        c =
          (((d - p) / 2 + p - this.pref.getPH2O()) * (1 - n - s)) /
          this.pref.getPConversion();
        this.oxTox.addO2(u, c);
        r = c;
      }
      for (o = 0; o < this.COMPS; o++) {
        this.tissues[o].ascDec(
          a,
          h,
          l,
          f,
          u,
          t,
          e,
          this.bailout,
          r,
          this.diveIndex,
        );
      }
    }
  }
  setTimeConstants(t) {
    if (!t) t = this.tissues;
    let e = [
      [1.88, 5, 16.189, 0.477, 11.696, 0.5578],
      [3.02, 8, 13.83, 0.5747, 10, 0.6514],
      [4.72, 12.5, 11.919, 0.6527, 8.618, 0.7222],
      [6.99, 18.5, 10.458, 0.7223, 7.562, 0.7825],
      [10.21, 27, 9.22, 0.7582, 6.2, 0.8126],
      [14.48, 38.3, 8.205, 0.7957, 5.043, 0.8434],
      [20.53, 54.3, 7.305, 0.8279, 4.41, 0.8693],
      [29.11, 77, 6.502, 0.8553, 4, 0.891],
      [41.2, 109, 5.95, 0.8757, 3.75, 0.9092],
      [55.19, 146, 5.545, 0.8903, 3.5, 0.9222],
      [70.69, 187, 5.333, 0.8997, 3.295, 0.9319],
      [90.34, 239, 5.189, 0.9073, 3.065, 0.9403],
      [115.29, 305, 5.181, 0.9122, 2.835, 0.9477],
      [147.42, 390, 5.176, 0.9171, 2.61, 0.9544],
      [188.24, 498, 5.172, 0.9217, 2.48, 0.9602],
      [240.03, 635, 5.119, 0.9267, 2.327, 0.9653],
    ];
    let i = [];
    let n = [];
    let s = [];
    let r = [];
    let o = [];
    let a = [];
    const h = 10.1;
    for (let t = 0; t < 16; t++) {
      if (this.pref.helium_half_time_multiplier >= 0) {
        s[t] =
          ((e[t][1] - e[t][0]) / h) * this.pref.helium_half_time_multiplier;
        i[t] =
          ((e[t][4] - e[t][2]) / h) * this.pref.helium_half_time_multiplier;
        n[t] =
          ((e[t][5] - e[t][3]) / h) * this.pref.helium_half_time_multiplier;
        r[t] = 0;
        o[t] = 0;
        a[t] = 0;
      } else {
        a[t] =
          ((e[t][1] - e[t][0]) / h) * this.pref.helium_half_time_multiplier;
        r[t] =
          ((e[t][4] - e[t][2]) / h) * this.pref.helium_half_time_multiplier;
        o[t] =
          ((e[t][5] - e[t][3]) / h) * this.pref.helium_half_time_multiplier;
        s[t] = 0;
        i[t] = 0;
        n[t] = 0;
      }
    }
    if (this.modelName == "ZHL16C") {
      t[0].setCompartmentTimeConstants(
        0,
        1.88 + s[0],
        5 + a[0],
        16.189 + i[0],
        0.477 + n[0],
        11.696 + r[0],
        0.5578 + o[0],
      );
      t[1].setCompartmentTimeConstants(
        1,
        3.02 + s[1],
        8 + a[1],
        13.83 + i[1],
        0.5747 + n[1],
        10 + r[1],
        0.6514 + o[1],
      );
      t[2].setCompartmentTimeConstants(
        2,
        4.72 + s[2],
        12.5 + a[2],
        11.919 + i[2],
        0.6527 + n[2],
        8.618 + r[2],
        0.7222 + o[2],
      );
      t[3].setCompartmentTimeConstants(
        3,
        6.99 + s[3],
        18.5 + a[3],
        10.458 + i[3],
        0.7223 + n[3],
        7.562 + r[3],
        0.7825 + o[3],
      );
      t[4].setCompartmentTimeConstants(
        4,
        10.21 + s[4],
        27 + a[4],
        9.22 + i[4],
        0.7582 + n[4],
        6.2 + r[4],
        0.8126 + o[4],
      );
      t[5].setCompartmentTimeConstants(
        5,
        14.48 + s[5],
        38.3 + a[5],
        8.205 + i[5],
        0.7957 + n[5],
        5.043 + r[5],
        0.8434 + o[5],
      );
      t[6].setCompartmentTimeConstants(
        6,
        20.53 + s[6],
        54.3 + a[6],
        7.305 + i[6],
        0.8279 + n[6],
        4.41 + r[6],
        0.8693 + o[6],
      );
      t[7].setCompartmentTimeConstants(
        7,
        29.11 + s[7],
        77 + a[7],
        6.502 + i[7],
        0.8553 + n[7],
        4 + r[7],
        0.891 + o[7],
      );
      t[8].setCompartmentTimeConstants(
        8,
        41.2 + s[8],
        109 + a[8],
        5.95 + i[8],
        0.8757 + n[8],
        3.75 + r[8],
        0.9092 + o[8],
      );
      t[9].setCompartmentTimeConstants(
        9,
        55.19 + s[9],
        146 + a[9],
        5.545 + i[9],
        0.8903 + n[9],
        3.5 + r[9],
        0.9222 + o[9],
      );
      t[10].setCompartmentTimeConstants(
        10,
        70.69 + s[10],
        187 + a[10],
        5.333 + i[10],
        0.8997 + n[10],
        3.295 + r[10],
        0.9319 + o[10],
      );
      t[11].setCompartmentTimeConstants(
        11,
        90.34 + s[11],
        239 + a[11],
        5.189 + i[11],
        0.9073 + n[11],
        3.065 + r[11],
        0.9403 + o[11],
      );
      t[12].setCompartmentTimeConstants(
        12,
        115.29 + s[12],
        305 + a[12],
        5.181 + i[12],
        0.9122 + n[12],
        2.835 + r[12],
        0.9477 + o[12],
      );
      t[13].setCompartmentTimeConstants(
        13,
        147.42 + s[13],
        390 + a[13],
        5.176 + i[13],
        0.9171 + n[13],
        2.61 + r[13],
        0.9544 + o[13],
      );
      t[14].setCompartmentTimeConstants(
        14,
        188.24 + s[14],
        498 + a[14],
        5.172 + i[14],
        0.9217 + n[14],
        2.48 + r[14],
        0.9602 + o[14],
      );
      t[15].setCompartmentTimeConstants(
        15,
        240.03 + s[15],
        635 + a[15],
        5.119 + i[15],
        0.9267 + n[15],
        2.327 + r[15],
        0.9653 + o[15],
      );
    } else if (this.modelName == "ZHL16B") {
      t[0].setCompartmentTimeConstants(
        0,
        1.88 + s[0],
        5 + a[0],
        16.189 + i[0],
        0.477 + n[0],
        11.696 + r[0],
        0.5578 + o[0],
      );
      t[1].setCompartmentTimeConstants(
        1,
        3.02 + s[1],
        8 + a[1],
        13.83 + i[1],
        0.5747 + n[1],
        10 + r[1],
        0.6514 + o[1],
      );
      t[2].setCompartmentTimeConstants(
        2,
        4.72 + s[2],
        12.5 + a[2],
        11.919 + i[2],
        0.6527 + n[2],
        8.618 + r[2],
        0.7222 + o[2],
      );
      t[3].setCompartmentTimeConstants(
        3,
        6.99 + s[3],
        18.5 + a[3],
        10.458 + i[3],
        0.7223 + n[3],
        7.562 + r[3],
        0.7825 + o[3],
      );
      t[4].setCompartmentTimeConstants(
        4,
        10.21 + s[4],
        27 + a[4],
        9.22 + i[4],
        0.7582 + n[4],
        6.667 + r[4],
        0.8126 + o[4],
      );
      t[5].setCompartmentTimeConstants(
        5,
        14.48 + s[5],
        38.3 + a[5],
        8.205 + i[5],
        0.7957 + n[5],
        5.6 + r[5],
        0.8434 + o[5],
      );
      t[6].setCompartmentTimeConstants(
        6,
        20.53 + s[6],
        54.3 + a[6],
        7.305 + i[6],
        0.8279 + n[6],
        4.947 + r[6],
        0.8693 + o[6],
      );
      t[7].setCompartmentTimeConstants(
        7,
        29.11 + s[7],
        77 + a[7],
        6.502 + i[7],
        0.8553 + n[7],
        4.5 + r[7],
        0.891 + o[7],
      );
      t[8].setCompartmentTimeConstants(
        8,
        41.2 + s[8],
        109 + a[8],
        5.95 + i[8],
        0.8757 + n[8],
        4.187 + r[8],
        0.9092 + o[8],
      );
      t[9].setCompartmentTimeConstants(
        9,
        55.19 + s[9],
        146 + a[9],
        5.545 + i[9],
        0.8903 + n[9],
        3.798 + r[9],
        0.9222 + o[9],
      );
      t[10].setCompartmentTimeConstants(
        10,
        70.69 + s[10],
        187 + a[10],
        5.333 + i[10],
        0.8997 + n[10],
        3.497 + r[10],
        0.9319 + o[10],
      );
      t[11].setCompartmentTimeConstants(
        11,
        90.34 + s[11],
        239 + a[11],
        5.189 + i[11],
        0.9073 + n[11],
        3.223 + r[11],
        0.9403 + o[11],
      );
      t[12].setCompartmentTimeConstants(
        12,
        115.29 + s[12],
        305 + a[12],
        5.181 + i[12],
        0.9122 + n[12],
        2.85 + r[12],
        0.9477 + o[12],
      );
      t[13].setCompartmentTimeConstants(
        13,
        147.42 + s[13],
        390 + a[13],
        5.176 + i[13],
        0.9171 + n[13],
        2.737 + r[13],
        0.9544 + o[13],
      );
      t[14].setCompartmentTimeConstants(
        14,
        188.24 + s[14],
        498 + a[14],
        5.172 + i[14],
        0.9217 + n[14],
        2.523 + r[14],
        0.9602 + o[14],
      );
      t[15].setCompartmentTimeConstants(
        15,
        240.03 + s[15],
        635 + a[15],
        5.119 + i[15],
        0.9267 + n[15],
        2.327 + r[15],
        0.9653 + o[15],
      );
    }
    return t;
  }
  getAmbientPress() {
    let t, e, i, n, s, r, o, a, h, c, u, l, f;
    f = 6369;
    i = 9.80665;
    e = 28.9644;
    l = 8.31432;
    r = 288.15;
    h = 33;
    c = 10.1325;
    s = -6.5;
    a = (i * e) / l;
    t = this.pref.getAltitudeInMsw();
    n = t / 1e3;
    o = (n * f) / (n + f);
    u = r + s * o;
    const d = c * Math.exp((Math.log(r / u) * a) / s);
    const p = h * Math.exp((Math.log(r / u) * a) / s);
    return PI.isImperial() ? p : d;
  }
  doSurfaceInterval(t) {
    this.constDepth(0, t, 0, 0.79, 0, "surface");
    return true;
  }
  calc_inspired_gas(t, e, i, n, s, r) {
    if (!e || isNaN(e)) e = 0;
    if (!i || isNaN(i)) i = 0;
    let o = 1 - e - i;
    let a = this.pref.units == 0 ? t : PI.feetToMeters(t);
    if (this.pref.configuration == "CCR" && n != 0) {
      let t = s ? new FI(1 - e - i, e) : this.inputSegments[0].getGas();
      let r = t.getFHe() + t.getFN2();
      let h = t.getFHe() / r;
      let c = t.getFN2() / r;
      o =
        n /
        ((a + this.pref.getPConversioninMsw()) /
          this.pref.getPConversioninMsw());
      let u = 1 - o;
      let l = u * h;
      let f = u * c;
      if (o > 1) {
        o = 1;
        e = 0;
        i = 0;
      } else {
        e = l;
        i = f;
      }
    } else if (this.pref.configuration == "pSCR" && !this.pref.getOcDeco()) {
      if (o < 1 && r > 0) {
        let n = new ZI(this.rmv, this.metabolic_o2_consumption);
        let s =
          (this.outputSegmentsGasRuntime[e + "/" + i]
            ? this.outputSegmentsGasRuntime[e + "/" + i]
            : 0) + r;
        let h = n.PFavg(t, s, o * 100);
        let c =
          h /
          ((a + this.pref.getPConversioninMsw()) /
            this.pref.getPConversioninMsw());
        let u = 1 - c;
        let l = e / (e + i);
        let f = i / (e + i);
        let d = u * l;
        let p = u * f;
        e = d;
        i = p;
        o = c;
      } else {
        o = 1;
        e = 0;
        i = 0;
      }
    } else;
    let h = new FI(o, e, parseInt(t), n);
    return h;
  }
  addInspiredGasRuntime(t, e, i) {
    if (!this.outputSegmentsGasRuntime[t + "/" + e])
      this.outputSegmentsGasRuntime[t + "/" + e] = 0;
    this.outputSegmentsGasRuntime[t + "/" + e] += i;
  }
  doDive(t, i, n, s, r, o) {
    this.diveIndex = o;
    this.bailout = r;
    if (!t.metric) {
      this.pref.setUnitsTo(this.pref.IMPERIAL);
    } else {
      this.pref.setUnitsTo(this.pref.METRIC);
    }
    this.pref.setHelium_half_time_multiplier(t.helium_half_time_multiplier);
    this.pref.bottomppO2 = t.bottomppO2;
    this.pref.decoppO2 = t.decoppO2;
    this.pref.oxygenppO2 = t.oxygenppO2;
    this.pref.setAltitude(e.exports.toInteger(t.altitude_of_dive));
    this.pref.setGfLow(parseInt(t.gfLow) / 100);
    this.pref.setGfHigh(parseInt(t.gfHigh) / 100);
    this.pref.setGfLow_bailout(parseInt(t.gfLow_bailout) / 100);
    this.pref.setGfHigh_bailout(parseInt(t.gfHigh_bailout) / 100);
    let a = t.lastStop6m20ft ? (t.metric ? 6 : 20) : t.metric ? 3 : 10;
    this.pref.setLastStopDepth(a);
    this.pref.setStopDepthIncrement(t.decoStepSize);
    this.pref.setAscentRate(t.ascentRate);
    this.pref.setDescentRate(t.descentRate);
    this.pref.setConfiguration(t.configuration);
    this.pref.setOcDeco(t.configuration != "OC" ? false : true);
    this.pref.setBailout(r ? true : false);
    this.metabolic_o2_consumption = t.metabolic_o2_consumption;
    this.rmv = t.rmvBottom;
    this.descentppO2 = t.descentppO2;
    if (s === false) {
      this.isRepetitiveDive = false;
      this.setModel(t.buhlModel, r);
    } else {
      this.isRepetitiveDive = true;
      this.initGradient();
    }
    this.inputSegments = [];
    this.outputSegments = [];
    this.outputSegmentsGasRuntime = {};
    this.gases = [];
    this.runtime = 0;
    i.forEach((e) => {
      let i = new YI({}, this.pref);
      i.setDepth(parseFloat(e.depth));
      i.setTime(parseFloat(e.time));
      let n = e.gas;
      i.setGas(n);
      i.setSetpoint(
        e.setpoint && t.configuration == "CCR" ? parseFloat(e.setpoint) : 0,
      );
      i.setEnable(true);
      this.inputSegments.push(i);
    });
    for (let t in n) {
      let e = n[t];
      this.gases.push(e);
    }
    this.gases = e.exports.orderBy(this.gases, "fromDepth", "desc");
    let h = null;
    let c = null;
    let u = null;
    let l = null;
    let f = null;
    let d = true;
    c = new YI(this.inputSegments[0], this.pref);
    this.currentGas = c.getGas();
    this.currentDepth = 0;
    this.ppO2 = c.getSetpoint() > 0 ? this.descentppO2 : 0;
    this.inFinalAscent = false;
    this.inputSegments.forEach((t) => {
      c = t;
      if (c.getType() == this.pref.CONST) {
        u = c;
        f = u.getDepth() - this.currentDepth;
        if (f > 0) {
          let t = f / this.pref.getDescentRate();
          let e = u.getDepth() - (u.getDepth() - this.currentDepth) / 2;
          let i = this.calc_inspired_gas(
            e,
            this.currentGas.getFHe(),
            this.currentGas.getFN2(),
            this.ppO2,
            this.currentGas.getUseAsDiluent(),
            t,
          );
          this.ascDec(
            this.currentDepth,
            u.getDepth(),
            this.pref.getDescentRate(),
            i.getFHe(),
            i.getFN2(),
            this.ppO2,
          );
          this.outputSegments.push(
            new KI(
              this.currentDepth,
              u.getDepth(),
              this.pref.getDescentRate(),
              i,
              i.getpO2atDepth(u.getDepth() / 2, 1),
              this.pref,
            ),
          );
          this.addInspiredGasRuntime(
            this.currentGas.getFHe(),
            this.currentGas.getFN2(),
            t,
          );
          this.runtime += t;
        } else if (f < 0) {
          this.inFinalAscent = true;
          this.ascend(u.getDepth());
        }
        this.currentDepth = u.getDepth();
        this.ppO2 = u.getSetpoint();
        this.currentGas = c.getGas();
        let t = this.currentGas;
        if (u.getTime() > 0) {
          if (d) {
            t = this.calc_inspired_gas(
              this.currentDepth,
              this.currentGas.getFHe(),
              this.currentGas.getFN2(),
              this.ppO2,
              this.currentGas.getUseAsDiluent(),
              u.getTime() - this.runtime,
            );
            d = false;
            try {
              this.constDepth(
                u.getDepth(),
                u.getTime() - this.runtime,
                t.getFHe(),
                t.getFN2(),
                this.ppO2,
                "bottom",
              );
            } catch (t) {
              return this.PROCESSING_ERROR;
            }
            this.outputSegments.push(
              new XI(
                u.getDepth(),
                u.getTime() - this.runtime,
                t,
                this.pref.configuration == "CCR"
                  ? u.setpoint
                  : t.getpO2atDepth(u.getDepth(), 1),
                this.pref,
              ),
            );
            this.addInspiredGasRuntime(
              this.currentGas.getFHe(),
              this.currentGas.getFN2(),
              Math.abs(u.getTime() - this.runtime),
            );
            this.runtime = u.getTime();
          } else {
            t = this.calc_inspired_gas(
              this.currentDepth,
              this.currentGas.getFHe(),
              this.currentGas.getFN2(),
              this.ppO2,
              this.currentGas.getUseAsDiluent(),
              u.getTime(),
            );
            try {
              this.constDepth(
                u.getDepth(),
                u.getTime(),
                t.getFHe(),
                t.getFN2(),
                this.ppO2,
                "bottom",
              );
            } catch (t) {
              return this.PROCESSING_ERROR;
            }
            this.outputSegments.push(
              new XI(
                u.getDepth(),
                u.getTime(),
                t,
                this.pref.configuration == "CCR"
                  ? u.setpoint
                  : t.getpO2atDepth(u.getDepth(), 1),
                this.pref,
              ),
            );
            this.addInspiredGasRuntime(
              this.currentGas.getFHe(),
              this.currentGas.getFN2(),
              u.getTime(),
            );
            this.runtime += u.getTime();
          }
        } else {
          this.outputSegments.push(
            new XI(
              u.getDepth(),
              u.getTime(),
              t,
              this.pref.configuration == "CCR"
                ? u.setpoint
                : t.getpO2atDepth(u.getDepth(), 1),
              this.pref,
            ),
          );
        }
      }
    });
    this.inFinalAscent = true;
    this.pref.setOcDeco(t.configuration != "OC" && !r ? false : true);
    h = this.ascend(0);
    if (h != true) return h;
    l = 0;
    let p = [];
    this.decotime = 0;
    this.outputSegments.forEach((t) => {
      l += t.time;
      t.runtime = l;
      if (t.type != 2) {
        let e = {
          depth: t.depth,
          equal: {},
          gas: t.gas,
          linear: {},
          mix: 0,
          ppO2:
            t.setpoint > 0
              ? t.setpoint
              : t.gas.getpO2atDepth(this.currentDepth, 1),
          rangeShape: "model",
          rmv: 0,
          runtime: l,
          s: {},
          stage: this.pref.stage_descr[t.type],
          model: { runtime: l, stoptime: t.time },
        };
        p.push(e);
      }
      if (t.type == 4) {
        this.decotime += t.time;
      }
      this.runtime = l;
    });
    this.outputSegments = p;
    return this;
  }
  ascend(t) {
    let e = false;
    let i = false;
    let n = false;
    let s;
    let r = 0;
    let o;
    let a = 0;
    let h;
    let c = 0;
    let u;
    let l;
    if (this.inFinalAscent && this.pref.getOcDeco()) {
      this.currentGasIndex = -1;
      this.setDecoGas(this.currentDepth);
    }
    if (this.currentDepth < t) return this.PROCESSING_ERROR;
    if (this.currentDepth % this.pref.getStopDepthIncrement() > 0)
      h =
        (this.currentDepth / this.pref.getStopDepthIncrement()) *
        this.pref.getStopDepthIncrement();
    else h = this.currentDepth - this.pref.getStopDepthIncrement();
    if (h < t || this.currentDepth < this.pref.getStopDepthIncrement()) h = t;
    else if (this.currentDepth == this.pref.getLastStopDepth()) h = t;
    else if (h < this.pref.getLastStopDepth()) h = this.pref.getLastStopDepth();
    o = this.currentDepth;
    i = true;
    this.getGradient().setGfAtDepth(h);
    a = this.mValue(this.currentDepth);
    c = this.controlCompartment();
    let f = this.currentGas;
    while (this.currentDepth > t) {
      while (n || h < this.ceiling()) {
        e = true;
        n = false;
        if (i) {
          if (o > this.currentDepth) {
            let t = new KI(
              o,
              this.currentDepth,
              this.pref.getAscentRate(),
              f,
              f.getpO2atDepth(this.currentDepth, 1),
              this.pref,
            );
            this.outputSegments.push(t);
          }
          i = false;
        }
        if (
          (!this.pref.getGfMultilevelMode() || this.inFinalAscent) &&
          !this.getGradient().isGfSet()
        ) {
          this.getGradient().setGfSlopeAtDepth(this.currentDepth);
          this.getGradient().setGfAtDepth(h);
        }
        if (r == 0) {
          let t =
            Math.round(this.runtime / this.pref.getStopTimeIncrement() + 0.5) *
            this.pref.getStopTimeIncrement();
          s = t - this.runtime;
        } else {
          s = this.pref.getStopTimeIncrement();
        }
        if (s == 0) s = this.pref.getStopTimeIncrement();
        if (s > 0 && s <= 1) s = 1;
        r += s;
        f = this.calc_inspired_gas(
          this.currentDepth,
          this.currentGas.getFHe(),
          this.currentGas.getFN2(),
          this.ppO2,
          this.currentGas.getUseAsDiluent(),
          r,
        );
        this.constDepth(
          this.currentDepth,
          s,
          f.getFHe(),
          f.getFN2(),
          this.ppO2,
          "ascent",
        );
        if (r > 5e3) {
          return false;
        }
      }
      if (e) {
        this.runtime += r;
        n = true;
        l = new JI(
          this.currentDepth,
          r,
          f,
          f.getpO2atDepth(this.currentDepth, 1),
          this.pref,
        );
        l.setMvMax(a);
        l.setGfUsed(this.getGradient().getGf());
        l.setControlCompartment(c);
        this.outputSegments.push(l);
        this.addInspiredGasRuntime(
          this.currentGas.getFHe(),
          this.currentGas.getFN2(),
          r,
        );
        e = false;
        r = 0;
      } else if (i) {
        this.ascDec(
          this.currentDepth,
          h,
          this.pref.getAscentRate(),
          f.getFHe(),
          f.getFN2(),
          this.ppO2,
        );
        this.runtime +=
          (this.currentDepth - h) / (-1 * this.pref.getAscentRate());
      }
      this.currentDepth = h;
      a = this.mValue(this.currentDepth);
      c = this.controlCompartment();
      u = f;
      if (this.setDecoGas(this.currentDepth) == true) {
        if (i) {
          let t = new KI(
            o,
            this.currentDepth,
            this.pref.getAscentRate(),
            u,
            u.getpO2atDepth(this.currentDepth, 1),
            this.pref,
          );
          this.outputSegments.push(t);
          o = this.currentDepth;
        }
      }
      h = this.roundUpMultiple(
        this.currentDepth - this.pref.getStopDepthIncrement(),
        this.pref.getStopDepthIncrement(),
      );
      if (h < t || this.currentDepth < this.pref.getLastStopDepth()) h = t;
      else if (this.currentDepth == this.pref.getLastStopDepth()) h = t;
      else if (h < this.pref.getLastStopDepth())
        h = this.pref.getLastStopDepth();
      if (this.getGradient().isGfSet()) {
        this.getGradient().setGfAtDepth(h);
      }
    }
    if (i) {
      let t = new KI(
        o,
        this.currentDepth,
        this.pref.getAscentRate(),
        f,
        f.getpO2atDepth(this.currentDepth, 1),
        this.pref,
      );
      this.outputSegments.push(t);
    }
    return true;
  }
  roundUpMultiple(t, e) {
    return t + ((e - (t % e)) % e);
  }
  setDecoGas(t) {
    let e;
    let i = false;
    let n = false;
    if (!this.inFinalAscent) return false;
    if (this.gases.length == 0) return false;
    if (this.pref.getOcDeco() || this.pref.configuration == "pSCR") {
      this.currentGas = this.gases[0];
      this.currentGasIndex = 0;
      this.ppO2 = 0;
      while (!i && this.currentGasIndex + 1 < this.gases.length) {
        e = this.gases[this.currentGasIndex + 1];
        if (e.getFromDepth() >= t) {
          this.currentGasIndex += 1;
          if (this.currentGas.O2 <= e.O2) {
            this.currentGas = e;
            n = true;
          }
        } else {
          i = true;
        }
      }
    } else {
      this.ccr_currentGasIndex = 0;
      while (!i && this.ccr_currentGasIndex + 1 < this.gases.length) {
        e = this.gases[this.ccr_currentGasIndex + 1];
        if (e.getFromDepth() >= t || this.diveTools.depth2press(t) <= 1.7) {
          this.ccr_currentGasIndex += 1;
          this.currentGas = e;
          if (this.diveTools.depth2press(t) <= 1.7 && e.O2 < 95) {
            this.ppO2 = this.pref.oxygenppO2;
          } else {
            this.ppO2 = e.ppO2;
          }
          n = true;
        } else {
          i = true;
        }
      }
    }
    return n;
  }
}
