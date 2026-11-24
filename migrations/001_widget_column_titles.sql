ALTER TABLE dashboard_meta.sys_dashboard_widgets
    ADD COLUMN IF NOT EXISTS column_titles jsonb;

UPDATE dashboard_meta.sys_dashboard_widgets
SET column_titles = CASE WHEN upper(widget_type) IN ('TABLE','GRID','DATA_GRID','DATAGRID')
    THEN '{"product_category":"دسته‌بندی محصول","total_orders":"تعداد سفارشات","total_revenue":"درآمد کل (تومان)"}'::jsonb
    ELSE '{}'::jsonb END
WHERE column_titles IS NULL;

ALTER TABLE dashboard_meta.sys_dashboard_widgets
    ALTER COLUMN column_titles SET DEFAULT '{}'::jsonb,
    ALTER COLUMN column_titles SET NOT NULL;
