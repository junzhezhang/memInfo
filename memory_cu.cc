/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
#ifndef DISABLE_WARNINGS

#include "singa/core/memory.h"
#include "singa/utils/logging.h"
#include "singa/proto/core.pb.h"
#include <iostream>
#include <fstream>
#include <chrono>
#include <stdint.h>
// similar in core/device/platform.cc for use of cudaMemGetInfo
#include "singa/core/device.h"
#include "singa/singa_config.h"
#include "singa/utils/opencl_utils.h"
#include <cuda.h>

using namespace std;
#ifdef USE_CUDA

namespace singa {
std::atomic<int> CnMemPool::pool_count(0);
std::pair<size_t, size_t> CnMemPool::GetMemUsage() {
  size_t free, total;
  auto status = cnmemMemGetInfo(&free, &total, NULL);
  CHECK_EQ(status, cnmemStatus_t::CNMEM_STATUS_SUCCESS)
    << cnmemGetErrorString(status);
  return std::make_pair(free, total);
}

CnMemPool::CnMemPool(int numDevices, size_t init_size, size_t max_size) {
  for (int i = 0; i < numDevices; i++)
    conf_.add_device(i);
  conf_.set_init_size(init_size);
  conf_.set_max_size(max_size);
  CHECK_LT(++pool_count, 2) << "CnMemPool must be used as a singleton.";
}

CnMemPool::CnMemPool(const MemPoolConf &conf) {
  conf_ = conf;
  CHECK_LT(++pool_count, 2) << "CnMemPool must be used as a singleton.";
}

void CnMemPool::Init() {
  mtx_.lock();
  if (!initialized_) {
    const size_t kNBytesPerMB = (1u << 20);
    CHECK_GE(conf_.device_size(), 1);
    cnmemDevice_t *settingPtr = new cnmemDevice_t[conf_.device_size()];
    CHECK_GT(conf_.init_size(), 0u);
    int i = 0;
    for (auto device : conf_.device()) {
      settingPtr[i].device = device;
      settingPtr[i].size = conf_.init_size() * kNBytesPerMB;
      settingPtr[i].numStreams = 0;
      settingPtr[i].streams = NULL;
      settingPtr[i].streamSizes = 0;
      i++;
    }
    auto status = cnmemInit(conf_.device_size(), settingPtr, conf_.flag());
    CHECK_EQ(status, cnmemStatus_t::CNMEM_STATUS_SUCCESS)
        << " " << cnmemGetErrorString(status);
    delete[] settingPtr;
    initialized_ = true;
  }
  mtx_.unlock();
}

CnMemPool::~CnMemPool() {
  mtx_.lock();
  if (initialized_) {
    cnmemStatus_t status = cnmemFinalize();
    CHECK_EQ(status, cnmemStatus_t::CNMEM_STATUS_SUCCESS)
        << " " << cnmemGetErrorString(status);
    initialized_ = false;
    --pool_count;
  }
  mtx_.unlock();
}

void CnMemPool::Malloc(void **ptr, const size_t size) {
  if (!initialized_)
    Init();
  cnmemStatus_t status = cnmemMalloc(ptr, size, NULL);
  CHECK_EQ(status, cnmemStatus_t::CNMEM_STATUS_SUCCESS)
      << " " << cnmemGetErrorString(status);
  fstream file("memInfo.text", ios::in|ios::out|ios::app);
  int64_t now = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
  file<<"Malloc "<<*ptr<<' '<<size<<' '<<now<<endl;
  size_t free_byte=0;
  size_t total_byte=0;
  cudaMemGetInfo(&free_byte,&total_byte);
  double free_db = (double)free_byte ;
  double total_db = (double)total_byte ;
  double used_db = total_db - free_db ;
  fstream file2("cudaMem.text", ios::in|ios::out|ios::app);
  file2<<used_db/1024.0/1024.0<<' '<<free_db/1024.0/1024.0<<' '<<total_db/1024.0/1024.0<<endl;
  //FILE *pfile =fopen("cnmemMemoryState.log","a");
  //cnmemPrintMemoryState(pfile,NULL);
  //fclose(pfile);
}

void CnMemPool::Free(void *ptr) {
  CHECK(initialized_) << "Cannot free the memory as the pool is not initialzied";
  cnmemStatus_t status = cnmemFree(ptr, NULL);
  CHECK_EQ(status, cnmemStatus_t::CNMEM_STATUS_SUCCESS)
      << " " << cnmemGetErrorString(status);
  fstream file("memInfo.text", ios::in|ios::out|ios::app);
  int64_t now = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
  file<<"Free "<<ptr<<' '<<now<<endl;
  size_t free_byte=0;
  size_t total_byte=0;
  cudaMemGetInfo(&free_byte,&total_byte);
  double free_db = (double)free_byte ;
  double total_db = (double)total_byte ;
  double used_db = total_db - free_db ;
  fstream file2("cudaMem.text", ios::in|ios::out|ios::app);
  file2<<used_db/1024.0/1024.0<<' '<<free_db/1024.0/1024.0<<' '<<total_db/1024.0/1024.0<<endl;
  //FILE *pfile =fopen("cnmemMemoryState.log","a");
  //cnmemPrintMemoryState(pfile,NULL);
  //fclose(pfile);
}

// ===========================================================================
void CudaMemPool::Malloc(void **ptr, const size_t size) {
  cudaError_t status = cudaMalloc(ptr, size);
  CHECK_EQ(status, cudaError_t::cudaSuccess);
}

void CudaMemPool::Free(void *ptr) {
  cudaError_t status = cudaFree(ptr);
  CHECK_EQ(status, cudaError_t::cudaSuccess);
}
}
#endif

#endif
