package com.parabank.perf.support;

import io.gatling.javaapi.http.HttpProtocolBuilder;
import java.net.URI;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.Arrays;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;
import static io.gatling.javaapi.http.HttpDsl.http;

public final class Environment {
  private Environment() {}
  public static final String BASE_URL = required("BASE_URL", "http://localhost:8080/parabank/services/bank");
  public static final String PROFILE = System.getenv().getOrDefault("PROFILE", "smoke").toLowerCase(Locale.ROOT);
  public static final int DURATION = positiveInt("DURATION_SECONDS", PROFILE.equals("smoke") ? 10 : 300);
  public static final int RAMP = positiveInt("RAMP_SECONDS", 60);
  public static final int USERS = positiveInt("USERS", PROFILE.equals("smoke") ? 2 : 100);
  public static final int RATE = positiveInt("RATE_PER_SECOND", 165);
  public static final String DATA_DIR = System.getenv().getOrDefault("DATA_DIR", "data");

  static {
    URI uri = URI.create(BASE_URL);
    if (!Set.of("http", "https").contains(uri.getScheme()) || uri.getHost() == null || uri.getUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null)
      throw new IllegalArgumentException("BASE_URL must be an HTTP(S) origin/path without credentials, query, or fragment");
    Set<String> allowed = Arrays.stream(System.getenv().getOrDefault("ALLOWED_HOSTS", "localhost,127.0.0.1").split(","))
        .map(String::trim).filter(s -> !s.isEmpty()).collect(Collectors.toSet());
    String host = uri.getHost().toLowerCase(Locale.ROOT);
    boolean privateAddress = host.equals("localhost") || host.equals("::1") || host.startsWith("127.") || host.startsWith("10.") || host.startsWith("192.168.") || host.matches("172\\.(1[6-9]|2[0-9]|3[01])\\..*");
    try {
      privateAddress = privateAddress || java.util.Arrays.stream(InetAddress.getAllByName(host)).allMatch(address -> address.isLoopbackAddress() || address.isSiteLocalAddress() || address.isLinkLocalAddress());
    } catch (UnknownHostException e) {
      throw new IllegalArgumentException("BASE_URL host must resolve to the isolated private instance", e);
    }
    if (host.equals("parabank.parasoft.com")) throw new IllegalArgumentException("The public ParaBank site is never an allowed performance target");
    boolean loopback = host.equals("localhost") || host.equals("::1") || host.startsWith("127.");
    if (!privateAddress || !loopback && !allowed.contains(host))
      throw new IllegalArgumentException("Refusing target. It must resolve privately and be listed in ALLOWED_HOSTS.");
    if (PROFILE.equals("smoke") && (USERS > 5 || DURATION > 60))
      throw new IllegalArgumentException("Smoke profile is limited to 5 users, 5 requests/s, and 60 seconds");
    if (!Set.of("smoke", "normal", "peak", "stress").contains(PROFILE)) throw new IllegalArgumentException("PROFILE must be smoke, normal, peak, or stress");
  }

  public static HttpProtocolBuilder httpProtocol() {
    return http.baseUrl(BASE_URL).acceptHeader("application/json, application/xml, text/xml, */*")
        .contentTypeHeader("application/json").userAgentHeader("parabank-gatling-performance");
  }
  public static int positiveInt(String name, int fallback) {
    String raw = System.getenv(name);
    int value = raw == null || raw.isBlank() ? fallback : Integer.parseInt(raw);
    if (value <= 0) throw new IllegalArgumentException(name + " must be positive");
    return value;
  }
  private static String required(String key, String fallback) { return System.getenv().getOrDefault(key, fallback); }
}
