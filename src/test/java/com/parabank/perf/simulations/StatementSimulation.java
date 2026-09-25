package com.parabank.perf.simulations;

import com.parabank.perf.support.Environment;
import com.parabank.perf.support.SimulationSupport;
import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public class StatementSimulation extends SimulationSupport {
  public StatementSimulation() {
    var scenario = scenario("H3 statement").feed(csv(dataDir + "/statements.csv").circular())
      .exec(http("statement").get("/accounts/#{accountId}/transactions")
        .check(status().is(200), jsonPath("$[0].id").exists()));
    int count = Environment.PROFILE.equals("smoke") ? users : 200;
    var setup = Environment.PROFILE.equals("smoke") || Environment.PROFILE.equals("peak") || Environment.PROFILE.equals("stress")
      ? scenario.injectOpen(atOnceUsers(count)) : scenario.injectClosed(closed(200));
    setUp(setup).protocols(Environment.httpProtocol())
      .assertions(details("statement").responseTime().max().lte(3000), global().failedRequests().percent().lte(1.0));
  }
}
