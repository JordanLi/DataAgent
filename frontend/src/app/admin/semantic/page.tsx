"use client";

import React from "react";
import { SemanticEditor } from "@/components/admin/SemanticEditor";

export default function SemanticPage() {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Semantic Layer Configuration</h1>
      <SemanticEditor />
    </div>
  );
}
