package com.parabank.perf.support;

import io.gatling.javaapi.core.Simulation;
import java.time.Duration;
import static io.gatling.javaapi.core.CoreDsl.*;

public abstract class SimulationSupport extends Simulation {
  protected final int duration = Environment.DURATION;
  protected final int ramp = Environment.RAMP;
  protected final int users = Environment.USERS;
  protected final String dataDir = Environment.DATA_DIR;

  protected io.gatling.javaapi.core.ClosedInjectionStep[] closed(int normalUsers) {
    int count = Environment.PROFILE.equals("smoke") ? users : normalUsers;
    int rampSeconds = Environment.PROFILE.equals("smoke") ? Math.min(ramp, 10) : ramp;
    int stableSeconds = Environment.PROFILE.equals("smoke") ? Math.min(duration, 10) : duration;
    return new io.gatling.javaapi.core.ClosedInjectionStep[]{rampConcurrentUsers(0).to(count).during(Duration.ofSeconds(rampSeconds)), constantConcurrentUsers(count).during(Duration.ofSeconds(stableSeconds))};
  }
  protected static int effectiveRate(int normalRate) { return Environment.PROFILE.equals("smoke") ? Math.min(Environment.RATE, 5) : normalRate; }
}
