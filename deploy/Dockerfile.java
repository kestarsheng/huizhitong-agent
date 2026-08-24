# 汇智通 Java 服务镜像：运行时（eclipse-temurin 17 JRE），jar 由宿主机构建后打入
FROM eclipse-temurin:17-jre

ARG JAR_FILE
COPY ${JAR_FILE} /app/app.jar
WORKDIR /app
ENTRYPOINT ["java", "-jar", "/app/app.jar"]