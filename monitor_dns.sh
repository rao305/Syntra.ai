#!/bin/bash
# Monitor DNS propagation for Supabase

echo "🔍 Monitoring DNS propagation for Supabase..."
echo "Hostname: db.lqjktbfjnbunvitujiiu.supabase.co"
echo ""

while true; do
    echo "$(date): Checking DNS resolution..."
    
    if nslookup db.lqjktbfjnbunvitujiiu.supabase.co >/dev/null 2>&1; then
        echo "✅ DNS RESOLVED! Ready for cutover."
        echo ""
        echo "🚀 Execute: bash /Users/rao305/Documents/Syntra/cutover_execution.sh"
        break
    else
        echo "❌ DNS not resolving yet. Waiting 5 minutes..."
        sleep 300
    fi
done
