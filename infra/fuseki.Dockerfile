FROM eclipse-temurin:21-jre
ADD https://repo.maven.apache.org/maven2/org/apache/jena/jena-fuseki-server/5.4.0/jena-fuseki-server-5.4.0.jar /fuseki.jar
RUN mkdir -p /data
EXPOSE 3030
ENTRYPOINT ["java", "-Xmx512m", "-jar", "/fuseki.jar", "--update", "--loc=/data", "/catalog"]
