import java.util.ArrayList;
import java.util.List;

/**
 * VpmbGfsEngine - Decompression Profile Calculator
 * Integrates Variable Permeability Model (VPM-B) bubble dynamics 
 * with Bühlmann Gradient Factor Safety (GFS) constraints.
 */
public class VpmbGfsEngine {

    private static final double ATM = 101325.0;                      
    private static final double WATER_VAPOR_PRESSURE = 6270.0;       
    private static final double SURFACE_TENSION_GAMMA = 0.0154;      
    private static final double SKIN_COMPRESSION_GAMMAC = 0.257;     
    private static final double CRIT_VOLUME_LAMBDA = 0.00418;        
    private static final int NUM_COMPARTMENTS = 16;

    public static class GasMix {
        public final double fO2;
        public final double fHe;
        public final double fN2;
        public final String name;

        public GasMix(double o2, double he, String name) {
            this.fO2 = o2;
            this.fHe = he;
            this.fN2 = 1.0 - o2 - he;
            this.name = name;
        }
    }

    private static class Compartment {
        final double halfTimeN2;
        final double halfTimeHe;
        final double buhlmannA;
        final double buhlmannB;
        
        double pN2;
        double pHe;
        
        double maxCrushPN2;
        double r0N2;
        double allowableGradN2;
        double initialAllowableGradN2;

        Compartment(double htN2, double htHe, double a, double b) {
            this.halfTimeN2 = htN2;
            this.halfTimeHe = htHe;
            this.buhlmannA = a;
            this.buhlmannB = b;
            this.pN2 = (ATM - WATER_VAPOR_PRESSURE) * 0.79; 
            this.pHe = 0.0;
            this.maxCrushPN2 = 0.0;
            this.r0N2 = 0.8e-6; 
            this.allowableGradN2 = 0.0;
            this.initialAllowableGradN2 = 0.0;
        }

        void updateGasLoading(double depthStartMeters, double depthEndMeters, double timeMin, GasMix gas) {
            double depthStartBar = 1.0 + (depthStartMeters / 10.0);
            double depthEndBar = 1.0 + (depthEndMeters / 10.0);
            
            double pN2Start = ((depthStartBar * 100000.0) - WATER_VAPOR_PRESSURE) * gas.fN2;
            double pN2End   = ((depthEndBar * 100000.0) - WATER_VAPOR_PRESSURE) * gas.fN2;
            double pHeStart = ((depthStartBar * 100000.0) - WATER_VAPOR_PRESSURE) * gas.fHe;
            double pHeEnd   = ((depthEndBar * 100000.0) - WATER_VAPOR_PRESSURE) * gas.fHe;

            double kN2 = Math.log(2.0) / halfTimeN2;
            double kHe = Math.log(2.0) / halfTimeHe;

            this.pN2 = solveSchreiner(pN2Start, pN2End, timeMin, kN2, this.pN2);
            this.pHe = solveSchreiner(pHeStart, pHeEnd, timeMin, kHe, this.pHe);
        }

        private double solveSchreiner(double pStart, double pEnd, double t, double k, double pInitial) {
            double r = (pEnd - pStart) / t;
            if (r != 0.0) {
                return pStart + r * (t - (1.0 / k)) + (pInitial - pStart + (r / k)) * Math.exp(-k * t);
            } else {
                return pStart + (pInitial - pStart) * Math.exp(-k * t);
            }
        }
    }

    private final List<Compartment> compartments = new ArrayList<>(NUM_COMPARTMENTS);
    private final double gfHigh;

    public VpmbGfsEngine(double gfHighSetting) {
        this.gfHigh = gfHighSetting;

        double[] HT_N2 = {5.0, 8.0, 12.5, 18.5, 27.0, 38.3, 54.3, 77.0, 109.0, 146.0, 187.0, 239.0, 305.0, 390.0, 498.0, 635.0};
        double[] HT_HE = {1.88, 3.02, 4.72, 6.99, 10.21, 14.48, 20.53, 29.11, 41.20, 55.19, 70.69, 90.34, 115.29, 147.42, 188.24, 240.03};
        double[] A_N2  = {1.2599, 1.0000, 0.8618, 0.7562, 0.6667, 0.5933, 0.5282, 0.4701, 0.4187, 0.3798, 0.3497, 0.3223, 0.2971, 0.2737, 0.2523, 0.2137};
        double[] B_N2  = {0.5050, 0.6514, 0.7222, 0.7825, 0.8125, 0.8434, 0.8693, 0.8910, 0.9092, 0.9222, 0.9319, 0.9403, 0.9477, 0.9544, 0.9602, 0.9707};

        for (int i = 0; i < NUM_COMPARTMENTS; i++) {
            compartments.add(new Compartment(HT_N2[i], HT_HE[i], A_N2[i], B_N2[i]));
        }
    }

    public void executeBottomPhase(double maxDepthMeters, double bottomTimeMin, GasMix gas) {
        for (Compartment comp : compartments) {
            comp.updateGasLoading(0.0, maxDepthMeters, 2.0, gas); 
            comp.updateGasLoading(maxDepthMeters, maxDepthMeters, bottomTimeMin, gas);
        }

        double maxAmbientPa = (1.0 + (maxDepthMeters / 10.0)) * 100000.0;
        for (Compartment comp : compartments) {
            double crushN2 = maxAmbientPa - comp.pN2;
            if (crushN2 > comp.maxCrushPN2) {
                comp.maxCrushPN2 = crushN2;
                comp.r0N2 = 1.0 / ((1.0 / 0.8e-6) + (comp.maxCrushPN2 / (2.0 * (SKIN_COMPRESSION_GAMMAC - SURFACE_TENSION_GAMMA))));
            }
            comp.initialAllowableGradN2 = (2.0 * SURFACE_TENSION_GAMMA * (SKIN_COMPRESSION_GAMMAC - SURFACE_TENSION_GAMMA)) / 
                                          (comp.r0N2 * SKIN_COMPRESSION_GAMMAC);
            comp.allowableGradN2 = comp.initialAllowableGradN2;
        }
    }

    private double getEnforcedCeilingMeters(double currentAmbientPa, double stopTimeMin) {
        double maxVpmCeilingPa = ATM;
        double maxBuhlmannCeilingPa = ATM;

        for (Compartment comp : compartments) {
            double lowerBound = 0.0;
            double upperBound = comp.initialAllowableGradN2;
            double activeGrad = comp.allowableGradN2;

            for (int j = 0; j < 25; j++) {
                double expansionFactor = ATM / currentAmbientPa;
                double adjustedRadius = comp.r0N2 * Math.cbrt(expansionFactor);
                double calcVolume = (activeGrad * stopTimeMin) / (adjustedRadius * ATM);
                double feedbackError = calcVolume - CRIT_VOLUME_LAMBDA;

                if (Math.abs(feedbackError) < 1.0) break;
                if (feedbackError > 0.0) upperBound = activeGrad;
                else lowerBound = activeGrad;
                activeGrad = (lowerBound + upperBound) / 2.0;
            }
            comp.allowableGradN2 = activeGrad;

            double totalTension = comp.pN2 + comp.pHe;
            double vpmCeilPa = totalTension - comp.allowableGradN2;
            if (vpmCeilPa > maxVpmCeilingPa) maxVpmCeilingPa = vpmCeilPa;

            double totalTensionBar = totalTension / 100000.0;
            double rawCeilingBar = (totalTensionBar - comp.buhlmannA * gfHigh) / (gfHigh / comp.buhlmannB + 1.0 - gfHigh);
            double buhlmannCeilPa = rawCeilingBar * 100000.0;
            if (buhlmannCeilPa > maxBuhlmannCeilingPa) maxBuhlmannCeilingPa = buhlmannCeilPa;
        }

        double maxEnforcedPa = Math.max(maxVpmCeilingPa, maxBuhlmannCeilingPa);
        double calculatedMeters = (maxEnforcedPa - ATM) / 10000.0;
        return Math.max(0.0, calculatedMeters);
    }

    public void generateAscentSchedule(double startDepthMeters, GasMix bottomGas, GasMix decoGas, double gasSwitchDepth) {
        System.out.println("\n========================================================");
        System.out.println("          RUNNING VPM-B/GFS ENGINE SIMULATION          ");
        System.out.println("========================================================");
        System.out.format("%-15s %-15s %-15s\n", "Depth (meters)", "Stop Time (min)", "Active Gas");
        System.out.println("--------------------------------------------------------");

        double currentDepth = startDepthMeters;
        GasMix activeGas = bottomGas;
        boolean gasSwitched = false;

        while (currentDepth > 0) {
            if (!gasSwitched && currentDepth <= gasSwitchDepth) {
                activeGas = decoGas;
                gasSwitched = true;
                System.out.format("%-15s %-15s %-15s\n", "--- " + currentDepth + "m ---", "GAS SWITCH", "-> " + activeGas.name);
            }

            double nextStopDepth = Math.floor((currentDepth - 0.1) / 3.0) * 3.0;
            if (nextStopDepth < 0) nextStopDepth = 0;

            double travelTimeMin = (currentDepth - nextStopDepth) / 10.0;
            for (Compartment comp : compartments) {
                comp.updateGasLoading(currentDepth, nextStopDepth, travelTimeMin, activeGas);
            }
            
            currentDepth = nextStopDepth;
            if (currentDepth == 0) break;

            int stopMinutes = 0;
            int loopGuard = 0; 
            
            while (loopGuard < 120) { 
                loopGuard++;
                double currentAmbientPa = (1.0 + (currentDepth / 10.0)) * 100000.0;
                double requiredCeilingMeters = getEnforcedCeilingMeters(currentAmbientPa, 1.0);

                if (requiredCeilingMeters > (currentDepth - 3.0)) {
                    stopMinutes++;
                    for (Compartment comp : compartments) {
                        comp.updateGasLoading(currentDepth, currentDepth, 1.0, activeGas);
                    }
                } else {
                    break;
                }
            }

            if (stopMinutes > 0) {
                System.out.format("%-15.0fm %-15d %-15s\n", currentDepth, stopMinutes, activeGas.name);
            }
        }
        System.out.println("--------------------------------------------------------");
        System.out.println(">>> 0m              SURFACE      Simulation completed.");
        System.out.println("========================================================");
    }

    public static void main(String[] args) {
        VpmbGfsEngine engine = new VpmbGfsEngine(0.90);
        GasMix bottomGas = new GasMix(0.16, 0.50, "Trimix 16/50");
        GasMix decoGas = new GasMix(0.50, 0.0, "Nitrox 50%");
        
        engine.executeBottomPhase(60.0, 30.0, bottomGas);
        engine.generateAscentSchedule(60.0, bottomGas, decoGas, 21.0);
    }
}
