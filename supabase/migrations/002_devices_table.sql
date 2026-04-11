-- 设备表：存储 ESP32-S3 设备绑定信息
-- 运行方式：Supabase Dashboard → SQL Editor → 粘贴执行

CREATE TABLE IF NOT EXISTS devices (
    id                  uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    device_id           text        NOT NULL UNIQUE,          -- ESP32 MAC 地址
    user_id             uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
    model               text        DEFAULT 'CoreS3',
    firmware_version    text        DEFAULT '0.1.0',
    device_token        text,                                  -- 配对成功后的永久 token
    pairing_code        text,                                  -- 6 位配对码（配对中有效）
    pairing_expires_at  timestamptz,
    paired_at           timestamptz,
    last_seen_at        timestamptz DEFAULT now(),
    created_at          timestamptz DEFAULT now()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_devices_user_id      ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_pairing_code ON devices(pairing_code) WHERE pairing_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_devices_device_token ON devices(device_token) WHERE device_token IS NOT NULL;

-- Row Level Security
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;

-- 用户只能看/改自己的设备（Service Key 可绕过 RLS，API 用 Service Key）
CREATE POLICY "users_own_devices" ON devices
    FOR ALL USING (auth.uid() = user_id);

-- 注释
COMMENT ON TABLE  devices                    IS 'Pixel AI 物理设备注册与绑定';
COMMENT ON COLUMN devices.device_id          IS 'ESP32 MAC 地址，格式如 AA:BB:CC:DD:EE:FF';
COMMENT ON COLUMN devices.device_token       IS '配对成功后发给设备的永久 token，存入 NVS Flash';
COMMENT ON COLUMN devices.pairing_code       IS '6位数字配对码，用户在 App 输入；配对完成后清空';
