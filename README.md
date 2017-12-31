# `diskorder` - read files in physical order to reduce hard drive seeks

Reading files in physical on-disk order can significantly reduce hard drive
seeks for spinning disks, and thus improve performance.

## Usage

Given some files (as arguments or stdin), `diskorder` prints them
sorted by physical order.

Assuming your current directory contains `hard.txt` and `drives.txt`:

```
$ ./diskorder.py hard.txt drives.txt
drives.txt
hard.txt
```

You can also pipe them in:

```
$ ls -1 | ./diskorder.py
diskorder.py
drives.txt
hard.txt
```

Use this with `tar`, `rsync` etc to get a significant reduction of seeks
and thus speedup for small files or on disk-busy systems.

On an otherwise idle system, this pays off when your files are smaller than
`yourHDspeedPerSecond / yourHdSpeedLatency`, so e.g. smaller than
`160 MB/s * 8 ms = 1.2 MB` for current generation hard drives.

Of course if your disk is not idle, it reduced seeks pay off even when your
files are much smaller.

## How it works

1. Get list of all files involved
2. Sort by physical address using the `FIEMAP` (file extent map) Linux `ioctl`
3. Access files in that order

Performance can be optionally be improved further by combining this
approach with `readahead()`.

## Example benchmark

On an Ubuntu 16.04 system:

```
$ du -sh /usr/lib
345M    /usr/lib

$ find /usr/lib | wc -l
8198

$ find /usr/lib -type f                  > files-in-find-order.txt
$ find /usr/lib -type f | ./diskorder.py > files-in-disk-order.txt

$ echo 3 > /proc/sys/vm/drop_caches # drop filesystem caches

$ time tar -c -T files-in-find-order.txt | cat > /dev/null
real    0m32.608s
user    0m0.088s
sys     0m1.048s

$ echo 3 > /proc/sys/vm/drop_caches # drop filesystem caches

$ time tar -c -T files-in-disk-order.txt | cat > /dev/null
ad7ac10cc07f3875dd493df33da3a4d5  -
real    0m15.621s
user    0m0.096s
sys     0m0.908s
```

Note we had to pipe `tar | cat`, otherwise tar is too smart and is much
faster (cheating).

Summary:

```
tar default        32 seconds
tar in disk order  16 seconds
```

**~2x speedup** in this case.

## Caveats

* Only works on Linux.
* Only tested with EXT4 so far.
* Probably doens't work for file systems that don't have extent
  or don't support `FIEMAP`.

## TODO

* Add warning when not used on spinning disks using the `BLKROTATIONAL` `ioctl`.
* Use O(n) integer sort for sorting physical addresses.
* Query only the first extent (`fm_extent_count = 1`) for a small performance
  improvement of `diskorder.py`.
* Write it in a faster language than Python.
  Python isn't a bottleneck as soon as the disk is involved
  (e.g. `time ./diskorder.py < files-in-find-order.txt > /dev/null` from
  the benchmark above runs in `real 0.314s, user 0.276s, sys 0.036s`
  which is negligible), but it's still slower than it could be.

## Acknowledgements

* [`Graeme`'s answer on StackOverflow](http://unix.stackexchange.com/questions/124527/speed-up-copying-1000000-small-files/124583#124583)
  which I found first
* [`mortehu`'s answer on StackOverflow](http://stackoverflow.com/questions/5144821/read-files-by-device-inode-order/15995139#15995139)
  and his contribution to use physical order in `dpkg`
  (with [example C code](http://lists.debian.org/debian-dpkg/2009/11/msg00002.html)),
  and the reference to the `BLKROTATIONAL` check for spinning disks.
* A [paper](http://home.ifi.uio.no/paalh/publications/files/ipccc09.pdf)
  about the topic that includes a `tar` benchmark,
  and corresponding [presentation](http://www.linux-kongress.org/2009/slides/linux_disk_io_performance_havard_espeland.pdf)
  from Linux-Congress.
  * After I asked the authors for it, they kindly released the source code of their [`qtar`](https://github.com/chlunde/qtar) implementation.
* [This blog post](http://dkrotx-prg.blogspot.ch/2012/08/speedup-file-reading-on-linux.html) by dkrotx.
* [Nicolas Trangez (@NicolasT)](https://gist.github.com/NicolasT)
  from whose [Gist I took the initial `fiemap.py`](https://gist.github.com/NicolasT/1237401).

## Similar work

* [platter-walk](https://github.com/the8472/platter-walk) - Rust library for HDD-aware directory traversal
* coretuils `rm -r` and other coreutils programs [sort files by inode order](http://git.savannah.gnu.org/cgit/coreutils.git/commit/?id=24412edeaf556a) before operating on them
  * However, I [found](https://bugs.python.org/issue32453#msg309303) that `rm -r` is still quadratic
* The authors of the [HTree](https://en.wikipedia.org/wiki/HTree) method that's used in `ext4` [write](http://ext2.sourceforge.net/2005-ols/paper-html/node3.html):
    > [...] it could cause some performance regressions for workloads that used readdir() to perform some operation of all of the files in a large directory [...] This performance regression can be easily fixed by modifying applications to **sort the directory entries** returned by readdir() **by inode number**
