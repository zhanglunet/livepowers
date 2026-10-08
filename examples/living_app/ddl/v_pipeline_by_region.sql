-- 生长出的固化结构：各地区在途商机金额（由次抛分析固化而来）
CREATE VIEW IF NOT EXISTS v_pipeline_by_region AS
SELECT c.region AS region, SUM(o.amount) AS amount, COUNT(*) AS n
FROM opportunities o JOIN customers c ON o.customer_id = c.id
WHERE o.stage NOT IN ('won', 'lost')
GROUP BY c.region;
