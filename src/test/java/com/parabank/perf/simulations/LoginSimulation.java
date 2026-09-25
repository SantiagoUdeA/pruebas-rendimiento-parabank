package com.parabank.perf.simulations;

import com.parabank.perf.support.Environment;
import com.parabank.perf.support.SimulationSupport;
import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

public class LoginSimulation extends SimulationSupport {
  public LoginSimulation() {
    var scenario = scenario("H1 login").feed(csv(dataDir + "/users.csv").circular())
      .exec(http("login").get("/login/#{username}/#{password}")
        .check(status().is(200), jsonPath("$.id").exists()));
    int count = Environment.PROFILE.equals("peak") || Environment.PROFILE.equals("stress") ? 200 : 100;
    int threshold = count == 200 ? 5000 : 2000;
    var setup = Environment.PROFILE.equals("smoke") ? scenario.injectOpen(atOnceUsers(users)) : scenario.injectClosed(closed(count));
    setUp(setup).protocols(Environment.httpProtocol())
      .assertions(details("login").responseTime().max().lte(threshold));
  }
}
