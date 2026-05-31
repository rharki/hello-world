# Database Scaling

A practical guide to scaling databases as your application grows. This document
covers the common strategies, when to reach for each, and the trade-offs
involved.

## Why Scaling Matters

As traffic and data volume grow, a single database instance eventually becomes a
bottleneck — whether on CPU, memory, disk I/O, or connection limits. Scaling is
about staying ahead of these limits while keeping the system reliable and
responsive.

Two broad approaches exist:

- **Vertical scaling (scale up):** Add more resources (CPU, RAM, faster disks)
  to a single machine.
- **Horizontal scaling (scale out):** Distribute load across multiple machines.

## Vertical Scaling

The simplest first step. Move to a bigger instance with more cores, memory, and
faster storage (e.g., NVMe SSDs).

**Pros**
- Simple — no application changes required.
- Preserves strong consistency and transactional guarantees.

**Cons**
- Hard ceiling — you can only buy so much machine.
- Single point of failure.
- Cost grows non-linearly at the high end.

## Horizontal Scaling

When vertical scaling runs out, distribute the workload.

### Read Replicas

Replicate writes from a primary to one or more read-only replicas. Route read
queries to replicas to offload the primary.

- Great for read-heavy workloads.
- Introduces **replication lag** — replicas may serve slightly stale data.
- Writes still funnel through a single primary.

### Sharding (Partitioning)

Split data across multiple databases ("shards"), each holding a subset of the
data. A shard key (e.g., `user_id`) determines where a row lives.

**Strategies**
- **Range-based:** Partition by value ranges (e.g., A–M, N–Z). Simple but prone
  to hotspots.
- **Hash-based:** Hash the shard key for even distribution. Harder to do range
  queries.
- **Directory-based:** A lookup service maps keys to shards. Flexible but adds a
  dependency.

**Trade-offs**
- Scales both reads and writes.
- Cross-shard queries and transactions become complex.
- Rebalancing shards is operationally expensive.

## Caching

Often the highest-leverage change. Put a cache (e.g., Redis, Memcached) in front
of the database to absorb repeated reads.

- **Cache-aside:** App checks cache, falls back to DB on miss, then populates.
- **Write-through / write-behind:** Writes go through the cache.

Watch out for cache invalidation and stampedes (many simultaneous misses).

## Other Techniques

- **Connection pooling** (e.g., PgBouncer) — reuse connections to avoid
  per-request overhead.
- **Indexing** — the cheapest win; ensure queries use appropriate indexes.
- **Denormalization** — trade write complexity for faster reads.
- **CQRS** — separate read and write models for independent scaling.
- **Archiving / TTL** — move cold data out of the hot path.

## Choosing a Strategy

A rough order of operations for most teams:

1. Optimize queries and add indexes.
2. Add caching for hot reads.
3. Scale vertically.
4. Add read replicas.
5. Introduce sharding only when necessary — it's the most complex step.

Measure before and after each change. The right strategy depends on your
read/write ratio, consistency requirements, and operational maturity.

## SQL vs. NoSQL Considerations

Some NoSQL databases (e.g., Cassandra, DynamoDB, MongoDB) are designed to scale
horizontally out of the box, trading strict consistency for availability and
partition tolerance (see the CAP theorem). Relational databases offer stronger
consistency but require more deliberate effort to scale out. Pick based on your
data model and consistency needs, not hype.
