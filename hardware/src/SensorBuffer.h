#ifndef SENSOR_BUFFER_H
#define SENSOR_BUFFER_H

#include <Arduino.h>

template <typename T, size_t N>
class CircularBuffer
{
private:
  T buffer[N];
  size_t head;
  size_t count;

public:
  CircularBuffer() : head(0), count(0) {}

  void push(T value)
  {
    buffer[head] = value;
    head = (head + 1) % N;
    if (count < N)
      count++;
  }

  T average(int configuredCount = 0) const
  {

    if (configuredCount > 0)
      return averageConfigured(configuredCount);

    if (count == 0)
      return 0;
    T sum = 0;

    for (size_t i = 0; i < count; i++)
    {
      sum += buffer[i];
    }
    return sum / count;
  }

  T averageConfigured(int configuredCount) const
  {
    if (count == 0 || configuredCount <= 0)
      return 0;
    T sum = 0;
    size_t elementsToConsider = (configuredCount < count) ? configuredCount : count;

    for (size_t i = 0; i < elementsToConsider; i++)
    {
      sum += buffer[i];
    }
    return sum / elementsToConsider;
  }

  T min() const
  {
    if (count == 0)
      return 0;
    T minVal = buffer[0];
    for (size_t i = 1; i < count; i++)
    {
      if (buffer[i] < minVal)
        minVal = buffer[i];
    }
    return minVal;
  }

  T max() const
  {
    if (count == 0)
      return 0;
    T maxVal = buffer[0];
    for (size_t i = 1; i < count; i++)
    {
      if (buffer[i] > maxVal)
        maxVal = buffer[i];
    }
    return maxVal;
  }

  bool isFull() const
  {
    return count == N;
  }

  size_t size() const
  {
    return count;
  }

  void clear()
  {
    count = 0;
    head = 0;
  }
};

#endif