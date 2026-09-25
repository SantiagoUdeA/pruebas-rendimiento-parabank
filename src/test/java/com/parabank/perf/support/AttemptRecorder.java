package com.parabank.perf.support;

import io.gatling.javaapi.core.Session;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.concurrent.atomic.AtomicLong;

/** Writes one small result row per financial attempt without logging request payloads. */
public final class AttemptRecorder {
  private static final Object LOCK = new Object();
  private static final AtomicLong ATTEMPT_SEQUENCE = new AtomicLong();
  private static final Path OUTPUT = Path.of(System.getenv().getOrDefault("ATTEMPTS_FILE", "evidence/runs/attempts.csv"));
  private static boolean initialized;
  private AttemptRecorder() {}

  public static Session record(Session session) {
    synchronized (LOCK) {
      try {
        Files.createDirectories(OUTPUT.toAbsolutePath().getParent());
        if (!initialized) {
          Files.writeString(OUTPUT, "caseId,status,amount,timestampMillis,fromAccountId,toAccountId,accountId\n", StandardCharsets.UTF_8,
              StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
          initialized = true;
        }
        String caseId = csv(session.getString("caseId") + "-" + ATTEMPT_SEQUENCE.incrementAndGet());
        String status = session.isFailed() ? "FAILED" : "CONFIRMED";
        String amount = csv(session.getString("amount"));
        String timestamp = Long.toString(System.currentTimeMillis());
        String from = optional(session, "fromAccountId");
        String to = optional(session, "toAccountId");
        String account = optional(session, "accountId");
        Files.writeString(OUTPUT, caseId + "," + status + "," + amount + "," + timestamp + "," + from + "," + to + "," + account + "\n", StandardCharsets.UTF_8,
            StandardOpenOption.APPEND);
      } catch (IOException e) {
        throw new IllegalStateException("Cannot write attempt reconciliation file", e);
      }
    }
    return session;
  }
  private static String optional(Session session, String key) { return session.contains(key) ? csv(session.getString(key)) : ""; }
  private static String csv(String value) { return "\"" + value.replace("\"", "\"\"") + "\""; }
}
