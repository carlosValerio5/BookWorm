import * as FileSystem from 'expo-file-system/legacy';

export const realBookScan = async (photoUri: string) => {
    try {
        console.log("Convirtiendo foto a Base64 para enviar al servidor...");
        const base64Image = await FileSystem.readAsStringAsync(photoUri, {
            encoding: FileSystem.EncodingType.Base64,
        });


        //Si lo quieren probar tiene que poner su ip
        const response = await fetch('http://192.168.1.193:8000/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: `data:image/jpeg;base64,${base64Image}` }),
        });

        if (!response.ok) {
            throw new Error(`Error en el servidor: ${response.status}`);
        }

        const data = await response.json();

        if (data.error || !data.title) {
            return { success: false, message: "No se pudo reconocer el libro. Intenta enfocar mejor la portada." };
        }

        return { success: true, data };

    } catch (error) {
        console.error("Error de conexión:", error);
        return { success: false, message: "Error de red con el servidor de BookWorm." };
    }
};
