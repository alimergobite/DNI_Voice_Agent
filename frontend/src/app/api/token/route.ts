import { NextRequest, NextResponse } from "next/server";
import { AccessToken } from "livekit-server-sdk";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { roomName, participantName, metadata } = body;

  if (!roomName || !participantName) {
    return NextResponse.json({ error: "roomName and participantName are required" }, { status: 400 });
  }

  const apiKey = process.env.LIVEKIT_API_KEY || "DNI_LIVEKIT_KEY";
  const apiSecret = process.env.LIVEKIT_API_SECRET || "DNI_LIVEKIT_SECRET_THAT_IS_LONG_ENOUGH_FOR_SECURITY";

  const token = new AccessToken(apiKey, apiSecret, {
    identity: participantName,
    name: participantName,
    metadata: metadata ? JSON.stringify(metadata) : undefined,
  });

  token.addGrant({ roomJoin: true, room: roomName, canPublish: true, canSubscribe: true });

  return NextResponse.json({ token: await token.toJwt() });
}
