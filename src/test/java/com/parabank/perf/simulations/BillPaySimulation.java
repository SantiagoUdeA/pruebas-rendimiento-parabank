package com.parabank.perf.simulations;

import com.parabank.perf.support.Environment;
import com.parabank.perf.support.SimulationSupport;
import com.parabank.perf.support.AttemptRecorder;
import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public class BillPaySimulation extends SimulationSupport {
  public BillPaySimulation() {
    var scenario = scenario("H5 bill pay").feed(csv(dataDir + "/payments.csv").circular())
      .exec(http("bill pay").post("/billpay?accountId=#{accountId}&amount=#{amount}")
        .body(StringBody("{\"name\":\"#{payeeName}\",\"address\":{\"street\":\"#{street}\",\"city\":\"#{city}\",\"state\":\"#{state}\",\"zipCode\":\"#{zipCode}\"},\"phoneNumber\":\"#{phone}\",\"accountNumber\":\"#{payeeAccount}\"}"))
        .check(status().is(200), jsonPath("$.payeeName").exists()))
      .pause(Environment.PAUSE)
      .exec(AttemptRecorder::record);
    int count = Environment.PROFILE.equals("smoke") ? users : 200;
    var setup = Environment.PROFILE.equals("smoke")
      ? scenario.injectOpen(atOnceUsers(users))
      : Environment.PROFILE.equals("peak") || Environment.PROFILE.equals("stress")
        ? scenario.injectOpen(stressPeakUsers(count).during(java.time.Duration.ofSeconds(Math.min(duration, 60))))
        : scenario.injectClosed(closed(200));
    setUp(setup).protocols(Environment.httpProtocol())
      .assertions(details("bill pay").responseTime().max().lte(3000), global().failedRequests().percent().lte(1.0));
  }
}
