import sys
from abc import ABC, abstractmethod


class Operacion(ABC):
    """Clase abstracta base para todas las operaciones matemáticas"""
    
    def __init__(self, num1: float, num2: float):
        """
        Inicializa la operación con dos números.
        
        Args:
            num1: Primer número
            num2: Segundo número
        """
        self.num1 = num1
        self.num2 = num2
    
    @abstractmethod
    def ejecutar(self) -> float:
        """Ejecuta la operación y retorna el resultado"""
        pass
    
    @abstractmethod
    def get_simbolo(self) -> str:
        """Retorna el símbolo de la operación"""
        pass


class Suma(Operacion):
    """Operación de suma"""
    
    def ejecutar(self) -> float:
        """Suma dos números"""
        return self.num1 + self.num2
    
    def get_simbolo(self) -> str:
        return "+"


class Resta(Operacion):
    """Operación de resta"""
    
    def ejecutar(self) -> float:
        """Resta dos números"""
        return self.num1 - self.num2
    
    def get_simbolo(self) -> str:
        return "-"


class Multiplicacion(Operacion):
    """Operación de multiplicación"""
    
    def ejecutar(self) -> float:
        """Multiplica dos números"""
        return self.num1 * self.num2
    
    def get_simbolo(self) -> str:
        return "*"


class Division(Operacion):
    """Operación de división"""
    
    def ejecutar(self) -> float:
        """Divide dos números"""
        if self.num2 == 0:
            raise ValueError("No se puede dividir entre cero")
        return self.num1 / self.num2
    
    def get_simbolo(self) -> str:
        return "/"


class Calculadora:
    """Clase que gestiona las operaciones matemáticas"""
    
    # Diccionario que mapea nombres de operaciones a sus clases
    OPERACIONES = {
        "suma": Suma,
        "resta": Resta,
        "multiplicacion": Multiplicacion,
        "division": Division
    }
    
    @staticmethod
    def obtener_operacion(nombre_operacion: str, num1: float, num2: float) -> Operacion:
        """
        Obtiene una instancia de la operación solicitada.
        
        Args:
            nombre_operacion: Nombre de la operación
            num1: Primer número
            num2: Segundo número
            
        Returns:
            Instancia de la operación
            
        Raises:
            ValueError: Si la operación no es reconocida
        """
        nombre_operacion = nombre_operacion.lower()
        
        if nombre_operacion not in Calculadora.OPERACIONES:
            operaciones_disponibles = ", ".join(Calculadora.OPERACIONES.keys())
            raise ValueError(
                f"Operación '{nombre_operacion}' no reconocida. "
                f"Disponibles: {operaciones_disponibles}"
            )
        
        return Calculadora.OPERACIONES[nombre_operacion](num1, num2)
    
    @staticmethod
    def calcular(nombre_operacion: str, num1: float, num2: float) -> tuple[float, str]:
        """
        Realiza el cálculo de la operación especificada.
        
        Args:
            nombre_operacion: Nombre de la operación
            num1: Primer número
            num2: Segundo número
            
        Returns:
            Tupla (resultado, símbolo) de la operación
            
        Raises:
            ValueError: Si hay un error en la operación
        """
        operacion = Calculadora.obtener_operacion(nombre_operacion, num1, num2)
        resultado = operacion.ejecutar()
        return resultado, operacion.get_simbolo()


class AplicacionCalculadora:
    """Aplicación principal de la calculadora"""
    
    def __init__(self):
        """Inicializa la aplicación"""
        self.calculadora = Calculadora()
    
    @staticmethod
    def validar_argumentos(args: list) -> tuple[str, float, float]:
        """
        Valida y procesa los argumentos de línea de comandos.
        
        Args:
            args: Lista de argumentos
            
        Returns:
            Tupla (operacion, num1, num2)
            
        Raises:
            ValueError: Si los argumentos no son válidos
        """
        if len(args) != 4:
            raise ValueError(
                "Uso: python app.py <operación> <número1> <número2>"
            )
        
        operacion = args[1]
        try:
            num1 = float(args[2])
            num2 = float(args[3])
        except ValueError:
            raise ValueError("Error: Los números deben ser valores numéricos válidos")
        
        return operacion, num1, num2
    
    def ejecutar(self, args: list) -> int:
        """
        Ejecuta la aplicación.
        
        Args:
            args: Lista de argumentos de línea de comandos
            
        Returns:
            Código de salida (0 = éxito, 1 = error)
        """
        try:
            operacion, num1, num2 = self.validar_argumentos(args)
            resultado, simbolo = self.calculadora.calcular(operacion, num1, num2)
            
            print(f"Resultado: {num1} {simbolo} {num2} = {resultado}")
            return 0
        
        except ValueError as e:
            print(f"Error: {e}")
            self.mostrar_ayuda()
            return 1
        except Exception as e:
            print(f"Error inesperado: {e}")
            return 1
    
    @staticmethod
    def mostrar_ayuda():
        """Muestra el mensaje de ayuda"""
        operaciones = ", ".join(Calculadora.OPERACIONES.keys())
        print(f"Operaciones disponibles: {operaciones}")


def main():
    """Función principal"""
    app = AplicacionCalculadora()
    codigo_salida = app.ejecutar(sys.argv)
    sys.exit(codigo_salida)


if __name__ == "__main__":
    main()
