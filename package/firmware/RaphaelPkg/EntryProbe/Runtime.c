/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * Freestanding string operations required by the pinned upstream libfdt.
 */
#include <stddef.h>

void *memcpy(void *dst, const void *src, size_t n)
{
  unsigned char *d = dst;
  const unsigned char *s = src;
  while (n--) *d++ = *s++;
  return dst;
}
void *memmove(void *dst, const void *src, size_t n)
{
  unsigned char *d = dst;
  const unsigned char *s = src;
  if (d <= s) while (n--) *d++ = *s++;
  else { d += n; s += n; while (n--) *--d = *--s; }
  return dst;
}
void *memset(void *dst, int value, size_t n)
{
  unsigned char *d = dst;
  while (n--) *d++ = (unsigned char)value;
  return dst;
}
int memcmp(const void *a, const void *b, size_t n)
{
  const unsigned char *x = a, *y = b;
  while (n--) { if (*x != *y) return *x - *y; ++x; ++y; }
  return 0;
}
void *memchr(const void *buffer, int value, size_t n)
{
  const unsigned char *p = buffer;
  while (n--) { if (*p == (unsigned char)value) return (void *)p; ++p; }
  return NULL;
}
size_t strlen(const char *s)
{
  const char *end = s;
  while (*end) ++end;
  return (size_t)(end - s);
}
size_t strnlen(const char *s, size_t n)
{
  size_t i = 0;
  while (i < n && s[i]) ++i;
  return i;
}
int strcmp(const char *a, const char *b)
{
  while (*a && *a == *b) { ++a; ++b; }
  return (unsigned char)*a - (unsigned char)*b;
}
int strncmp(const char *a, const char *b, size_t n)
{
  while (n--) {
    if (*a != *b || !*a) return (unsigned char)*a - (unsigned char)*b;
    ++a; ++b;
  }
  return 0;
}
char *strchr(const char *s, int value)
{
  for (;;) { if (*s == (char)value) return (char *)s; if (!*s++) return NULL; }
}
char *strrchr(const char *s, int value)
{
  const char *found = NULL;
  do { if (*s == (char)value) found = s; } while (*s++);
  return (char *)found;
}
