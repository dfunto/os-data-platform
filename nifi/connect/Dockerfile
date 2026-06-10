FROM confluentinc/cp-kafka-connect:7.6.0

# Hudi Kafka Connect bundle includes all dependencies (Hadoop, Avro, etc.)
RUN mkdir -p /usr/share/java/hudi && \
    curl -L https://repo1.maven.org/maven2/org/apache/hudi/hudi-kafka-connect-bundle/0.14.1/hudi-kafka-connect-bundle-0.14.1.jar \
    -o /usr/share/java/hudi/hudi-kafka-connect-bundle-0.14.1.jar