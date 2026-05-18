import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export async function GET() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    return NextResponse.json(
      { error: 'Supabase configuration environment variables are missing.' },
      { status: 500 }
    );
  }

  const supabase = createClient(supabaseUrl, supabaseAnonKey);

  try {
    // Calls our updated database function which now streams the heights
    const { data, error } = await supabase.rpc('get_buildings_geojson');

    if (error) throw error;

    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Database query failed:', error);
    return NextResponse.json(
      { error: 'Failed to fetch spatial data framework.', details: error.message },
      { status: 500 }
    );
  }
}