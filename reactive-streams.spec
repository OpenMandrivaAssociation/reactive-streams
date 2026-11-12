Name:		reactive-streams
Version:	1.0.2
Release:	1
Summary:	Reactive Streams interfaces for the JVM
Group:		Development/Java
License:	CC0-1.0
URL:		https://github.com/reactive-streams/reactive-streams-jvm
# Tag v1.0.2. The published jar is the four interfaces under org.reactivestreams.
Source0:	reactive-streams-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem

%description
org.reactivestreams:reactive-streams %{version}. Publisher, Subscriber,
Subscription, and Processor.

%prep
%autosetup -n reactive-streams-%{version} -p1
set -eo pipefail
python3 - << 'PY'
import os
bad = []
for dirpath, dirs, files in os.walk("."):
    for d in dirs:
        if d.endswith(".jar"):
            bad.append(os.path.join(dirpath, d))
    for fn in files:
        path = os.path.join(dirpath, fn)
        if fn.endswith((".jar", ".class", ".so", ".node", ".wasm", ".dll", ".a", ".o")):
            bad.append(path)
            continue
        try:
            with open(path, "rb") as fh:
                mag = fh.read(4)
        except OSError:
            continue
        if mag in (b"\x7fELF", b"\xca\xfe\xba\xbe"):
            bad.append(path)
if bad:
    print("\n".join(bad))
    raise SystemExit(1)
PY
test -s api/src/main/java/org/reactivestreams/Publisher.java
test -s api/src/main/java/org/reactivestreams/Subscriber.java
test -s api/src/main/java/org/reactivestreams/Subscription.java
test -s api/src/main/java/org/reactivestreams/Processor.java

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
find api/src/main/java -name '*.java' > srcs.list
test "$(wc -l < srcs.list)" -eq 4
mkdir -p classes
javac --release 8 -encoding UTF-8 -Xlint:-options -d classes @srcs.list
test "$(find classes -name '*.class' | wc -l)" -eq 4
printf '%%s\n' 'Manifest-Version: 1.0' 'Automatic-Module-Name: org.reactivestreams' "Implementation-Version: %{version}" > manifest.mf
jar cfm reactive-streams.jar manifest.mf -C classes .
jar i reactive-streams.jar
desc=$(jar --describe-module --file reactive-streams.jar)
printf '%%s\n' "$desc"
printf '%%s\n' "$desc" | grep -F -qx 'org.reactivestreams automatic'
if printf '%%s\n' "$desc" | grep -F -q Unable; then
	exit 1
fi
javap -v -classpath classes org.reactivestreams.Publisher | grep -F -q 'major version: 52'

cat > reactive-streams.pom << 'END'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.reactivestreams</groupId>
  <artifactId>reactive-streams</artifactId>
  <version>%{version}</version>
  <name>reactive-streams</name>
  <description>Reactive Streams interfaces for the JVM.</description>
  <url>https://github.com/reactive-streams/reactive-streams-jvm</url>
  <licenses>
    <license>
      <name>CC0-1.0</name>
      <url>https://creativecommons.org/publicdomain/zero/1.0/</url>
    </license>
  </licenses>
</project>
END

%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact reactive-streams.pom:reactive-streams.jar \
	--file-name reactive-streams \
	--filelist .mfiles
idx="%{buildroot}/usr/share/sysjar/index/org.reactivestreams/reactive-streams.sysjar"
test -s "$idx"
grep -F -q '"version": "%{version}"' "$idx"
grep -F -q '"artifactId": "reactive-streams"' "$idx"
test -s %{buildroot}%{_javadir}/reactive-streams.jar

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
JAR=%{buildroot}%{_javadir}/reactive-streams.jar
test -s "$JAR"
mkdir -p check
cat > check/RsCheck.java << 'END'
import org.reactivestreams.Publisher;
import org.reactivestreams.Subscriber;
import org.reactivestreams.Subscription;

public class RsCheck {
    public static void main(String[] args) {
        final int[] got = new int[1];
        Publisher<Integer> publisher = new Publisher<Integer>() {
            public void subscribe(Subscriber<? super Integer> subscriber) {
                subscriber.onSubscribe(new Subscription() {
                    public void request(long n) {
                        if (n > 0) {
                            subscriber.onNext(Integer.valueOf(1));
                            subscriber.onComplete();
                        }
                    }

                    public void cancel() {
                    }
                });
            }
        };
        publisher.subscribe(new Subscriber<Integer>() {
            public void onSubscribe(Subscription subscription) {
                subscription.request(1);
            }

            public void onNext(Integer value) {
                got[0] = value.intValue();
            }

            public void onError(Throwable error) {
                throw new RuntimeException(error);
            }

            public void onComplete() {
            }
        });
        if (got[0] != 1) {
            throw new RuntimeException(Integer.toString(got[0]));
        }
        System.out.println("reactive_streams_ok " + got[0]);
    }
}
END
javac --release 8 -encoding UTF-8 -Xlint:-options -cp "$JAR" -d check check/RsCheck.java
java -cp "check:$JAR" RsCheck > check/out.txt
cat check/out.txt
grep -F -qx 'reactive_streams_ok 1' check/out.txt

%files -f .mfiles
%license LICENSE
%doc README.md
