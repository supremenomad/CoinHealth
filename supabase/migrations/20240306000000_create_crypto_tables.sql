-- Create crypto_data table
CREATE TABLE IF NOT EXISTS crypto_data (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    coin_data JSONB NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(date, (coin_data->>'coingecko_id'))
);

-- Create index on date for faster queries
CREATE INDEX IF NOT EXISTS idx_crypto_data_date ON crypto_data(date);

-- Create index on coin_data fields for faster queries
CREATE INDEX IF NOT EXISTS idx_crypto_data_name ON crypto_data((coin_data->>'name'));
CREATE INDEX IF NOT EXISTS idx_crypto_data_symbol ON crypto_data((coin_data->>'symbol'));
CREATE INDEX IF NOT EXISTS idx_crypto_data_coingecko_id ON crypto_data((coin_data->>'coingecko_id'));

-- Enable Row Level Security (RLS)
ALTER TABLE crypto_data ENABLE ROW LEVEL SECURITY;

-- Create policy to allow public read access
CREATE POLICY "Allow public read access" ON crypto_data
    FOR SELECT
    USING (true);

-- Create policy to allow authenticated users to insert/update
CREATE POLICY "Allow authenticated users to insert/update" ON crypto_data
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated'); 