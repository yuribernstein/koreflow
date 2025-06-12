echo "Building Koreflow binaries for MacOS..."
./dev_utils/build.sh build_mac
echo "Building Koreflow binaries for Linux..."

docker build -t koreflow:linux -f ./dev_utils/Dockerfile.linux.build .
docker run --rm -v $(pwd)/build:/opt/koreflow/build koreflow:linux

echo "Binaries are available at build/koreflow"

echo "Building korectl binaries for MacOS..."
./korectl/build.sh 
