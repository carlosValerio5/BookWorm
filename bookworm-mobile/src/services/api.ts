import * as FileSystem from 'expo-file-system/legacy';

// Si lo quieren probar tiene que poner su ip
const MOBILE_API_HOST = '192.168.1.193:8000';

export type BoundingBox = { x_min: number; y_min: number; x_max: number; y_max: number };
export type BookDetectionBox = { confidence: number; box: BoundingBox };
export type IsbnBarcode = { isbn: string; box: BoundingBox };
export type RecognizedText = { text: string; confidence: number; box: BoundingBox };
export type ScanKind = 'isbn' | 'cover' | 'unknown';

export type ScanResult = {
    scan_id: string;
    image_path: string;
    kind: ScanKind;
    isbn: string | null;
    books: BookDetectionBox[];
    barcodes: IsbnBarcode[];
    texts: RecognizedText[];
};

export const realBookScan = async (photoUri: string) => {
    try {
        console.log("Convirtiendo foto a Base64 para enviar al servidor...");
        const base64Image = await FileSystem.readAsStringAsync(photoUri, {
            encoding: FileSystem.EncodingType.Base64,
        });

        const response = await fetch(`http://${MOBILE_API_HOST}/api/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: `data:image/jpeg;base64,${base64Image}` }),
        });

        if (!response.ok) {
            throw new Error(`Error en el servidor: ${response.status}`);
        }

        const data: ScanResult = await response.json();

        if (data.kind === 'unknown') {
            return { success: false, message: "No se pudo reconocer el libro. Intenta enfocar mejor la portada." };
        }

        return { success: true, data };

    } catch (error) {
        console.error("Error de conexión:", error);
        return { success: false, message: "Error de red con el servidor de BookWorm." };
    }
};

export const liveDetectWebSocketUrl = () => `ws://${MOBILE_API_HOST}/api/live-detect`;
