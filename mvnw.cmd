@echo off
setlocal
set BASE_DIR=%~dp0
java %MAVEN_OPTS% -classpath "%BASE_DIR%\.mvn\wrapper\maven-wrapper.jar" -Dmaven.multiModuleProjectDirectory="%BASE_DIR%" org.apache.maven.wrapper.MavenWrapperMain %*
