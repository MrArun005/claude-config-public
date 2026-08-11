---
name: local-run-setup
description: "How to build/run dpq-promotion-manager-service locally on Arun's machine — JDK 25 location, Nexus settings.xml, bdc profile, Kafka unreachable"
metadata: 
  node_type: memory
  type: project
  originSessionId: dc3cfe02-5ee0-41fe-b67a-ced10651a89b
  modified: 2026-07-27T08:55:11.990Z
---

Verified working local setup (2026-07-27) for dpq-promotion-manager-service:

- **JDK 25 required** to build (Tecnotree common-framework-parent sets java.version=25 + enforcer rule), even though bytecode target is 21. Portable JDK installed at `C:\Users\malliar\Java\jdk-25.0.3+9` (JAVA_HOME must point there for Maven; system default is still JDK 21).
- **Maven settings**: created `C:\Users\malliar\.m2\settings.xml` with Tecnotree Nexus repos (anonymous read works, no credentials).
- **Build**: `cd dclm && mvn clean install -DskipTests` → BUILD SUCCESS (~2.5 min).
- **Run**: `java -jar dclm/dpq-promotion-manager-service/target/dpq-promotion-manager-service.jar --spring.profiles.active=bdc` → starts in ~30s on port 8085, context path `/promotion-management/api`. Swagger basic auth swaggerAdmin/swaggerAdmin@123.
- **bdc profile** uses shared DIT MongoDB 172.20.21.212 (reachable from office network/VPN) and expects config dir `C:\user\local\tomcat\config\core` (exists on Arun's machine).
- **Kafka 10.40.176.17:31111 is NOT reachable** from Arun's machine — app still starts, just logs producer warnings; silence with `--kafka.health.check.enabled=false`. VZ_publicKey file missing from config dir (warning only).

**How to apply:** When building/running the BE, always set JAVA_HOME to the JDK 25 path first. Related: [[interview-prep-learning-plan]].
