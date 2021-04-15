#!/bin/sh
exec scala -classpath "geonorm-assembly-0.1.0-SNAPSHOT.jar" "$0" "$@"
!#


object HelloWorld {
  def main(args: Array[String]) {
    import scala.io.Source
		import scala.io.Source
/*
val filename = args(0)

for (line <- Source.fromFile(filename).getLines) {
    println(line)
}*/
		import org.clulab.geonorm._
		val indexTempDir = java.nio.file.Files.createTempDirectory("geonames")
		val index = GeoNamesIndex.fromClasspathJar(indexTempDir)
		val normalizer = new GeoLocationNormalizer(index)
		for (place <- args) {
			val test = normalizer(place);
			println(place)
			for (opt <- test){
				println(opt._1.name + ": " + opt._1.id)
			}
			println("\n");
		}
		//println(normalizer("Tucson").head)


 }
}
HelloWorld.main(args)
