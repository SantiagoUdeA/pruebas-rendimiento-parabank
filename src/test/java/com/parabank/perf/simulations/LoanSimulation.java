package com.parabank.perf.simulations;

import com.parabank.perf.support.Environment;
import com.parabank.perf.support.SimulationSupport;
import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public class LoanSimulation extends SimulationSupport {
  public LoanSimulation() {
    var scenario = scenario("H4 loan").feed(csv(dataDir + "/loans.csv").queue())
      .exec(http("request loan").post("/requestLoan?customerId=#{customerId}&amount=#{amount}&downPayment=#{downPayment}&fromAccountId=#{fromAccountId}")
        .check(status().is(200), jsonPath("$.loanProviderName").exists(), jsonPath("$.approved").is("true")));
    var setup = Environment.PROFILE.equals("smoke") ? scenario.injectOpen(atOnceUsers(1)) : scenario.injectClosed(closed(150));
    setUp(setup).protocols(Environment.httpProtocol())
      .assertions(details("request loan").responseTime().mean().lte(5000), details("request loan").successfulRequests().percent().gte(98.0));
  }
}
