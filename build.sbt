scalaVersion := 2.12.12

resolvers += (Artifactory at http://artifactory.cs.arizona.edu:8081/artifactory/sbt-release-local/).withAllowInsecureProtocol(true)

libraryDependencies ++= Seq(

                org.clulab %% geonorm % 1.0.0,

                org.clulab % geonames % 1.0.0+20200404T005315Z,

)
