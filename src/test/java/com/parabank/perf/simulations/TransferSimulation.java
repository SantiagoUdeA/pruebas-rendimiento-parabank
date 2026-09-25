package com.parabank.perf.simulations;

import com.parabank.perf.support.Environment;
import com.parabank.perf.support.SimulationSupport;
import com.parabank.perf.support.AttemptRecorder;
import java.time.Duration;
import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public class TransferSimulation extends SimulationSupport {
  public TransferSimulation() {
    var scenario = scenario("H2 transfer").feed(csv(dataDir + "/transfers.csv").queue())
      .exec(http("transfer").post("/transfer?fromAccountId=#{fromAccountId}&toAccountId=#{toAccountId}&amount=#{amount}")
        .check(status().is(200), substring("Successfully transferred").exists()))
      .exec(AttemptRecorder::record);
    int rate = effectiveRate(165);
    var injection = Environment.PROFILE.equals("smoke")
      ? new io.gatling.javaapi.core.OpenInjectionStep[]{constantUsersPerSec(rate).during(Duration.ofSeconds(Math.min(duration, 10)))}
      : new io.gatling.javaapi.core.OpenInjectionStep[]{rampUsersPerSec(0).to(rate).during(Duration.ofSeconds(ramp)), constantUsersPerSec(rate).during(Duration.ofSeconds(duration))};
    setUp(scenario.injectOpen(injection)).protocols(Environment.httpProtocol())
      .assertions(details("transfer").failedRequests().count().is(0L));
  }
}
